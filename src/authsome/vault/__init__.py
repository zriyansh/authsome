"""Vault — encrypted key-value layer over AppStore."""

from __future__ import annotations

import base64
import builtins
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from key_value.aio._utils.compound import uncompound_key
from loguru import logger

from authsome.store.interfaces import AppStore
from authsome.vault.crypto import _KEYRING_SERVICE, _KEYRING_USERNAME, VaultCrypto, _AesGcmCrypto, create_crypto

kr: Any
try:
    import keyring

    kr = keyring
except ImportError:
    kr = None

if TYPE_CHECKING:
    from authsome.vault.crypto import VaultCrypto


class Vault:
    """Encrypted key-value store backed by an AppStore.

    All values are encrypted at rest using AES-256-GCM.  The master key is
    managed by the configured VaultCrypto backend (local file or OS keyring).
    """

    def __init__(
        self,
        app_store: AppStore,
        crypto: VaultCrypto | None = None,
        crypto_mode: str = "auto",
        master_key_path: Path | None = None,
    ) -> None:
        self._app_store = app_store
        self._crypto = crypto
        self._crypto_mode = crypto_mode
        self._master_key_path = master_key_path

    @property
    def crypto(self) -> VaultCrypto:
        if self._crypto is None:
            self._crypto = create_crypto(self._master_key_path, self._crypto_mode)
        return self._crypto

    @property
    def crypto_mode(self) -> str:
        """Configured crypto resolution mode."""
        return self._crypto_mode

    @property
    def crypto_source(self) -> str:
        """Effective crypto source identifier."""
        return self.crypto.source_id

    @property
    def crypto_source_description(self) -> str:
        """Human-readable description of the effective crypto source."""
        return self.crypto.source_description

    # ── Index helpers ─────────────────────────────────────────────────────

    async def _get_index(self, collection: str) -> builtins.list[str]:
        val = await self._app_store.kv.get("__index__", collection=collection)
        if not val:
            return []
        return json.loads(val["data"])

    async def _save_index(self, collection: str, keys: builtins.list[str]) -> None:
        await self._app_store.kv.put("__index__", {"data": json.dumps(sorted(keys))}, collection=collection)

    # ── Encrypted KV interface ────────────────────────────────────────────

    async def get(self, key: str, *, collection: str) -> str | None:
        """Retrieve and decrypt a value. Returns None if key not found."""
        val = await self._app_store.kv.get(key, collection=collection)
        if val is None:
            return None
        return self.crypto.decrypt(val["data"])

    async def put(self, key: str, value: str, *, collection: str) -> None:
        """Encrypt and store a value."""
        encrypted = self.crypto.encrypt(value)
        await self._app_store.kv.put(key, {"data": encrypted}, collection=collection)
        if key != "__index__":
            idx = set(await self._get_index(collection))
            if key not in idx:
                idx.add(key)
                await self._save_index(collection, builtins.list(idx))

    async def delete(self, key: str, *, collection: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        existed = await self._app_store.kv.delete(key, collection=collection)
        if existed and key != "__index__":
            idx = set(await self._get_index(collection))
            idx.discard(key)
            await self._save_index(collection, builtins.list(idx))
        return existed

    async def list(self, prefix: str = "", *, collection: str) -> builtins.list[str]:
        """List all keys matching a prefix within a collection."""
        idx = await self._get_index(collection)
        if prefix:
            return [k for k in idx if k.startswith(prefix)]
        return list(idx)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def check_integrity(self, *, identity: str | None = None) -> bool:
        """Perform health check on underlying store."""
        _ = identity
        return await self._app_store.check_integrity()

    def _build_rekey_crypto(self, new_key_bytes: bytes) -> VaultCrypto:
        """Return an in-memory crypto backend used only during re-encryption."""

        class _RekeyCrypto(_AesGcmCrypto):
            def __init__(self, master_key: bytes) -> None:
                super().__init__(master_key)

            @property
            def source_id(self) -> str:
                return "rekey"

            @property
            def source_description(self) -> str:
                return "In-memory rekey backend"

        return _RekeyCrypto(new_key_bytes)

    async def rekey(self, new_key_bytes: bytes) -> None:
        """Re-encrypt all encrypted keys in the underlying KV store using a new master key."""
        old_crypto = self.crypto
        if old_crypto.source_id == "env":
            raise ValueError(
                "Vault rekey is unavailable while using AUTHSOME_MASTER_KEY. "
                "Update the external master key and migrate data from a writable backend first."
            )

        # 1. Create a new crypto instance using the new key
        new_crypto = self._build_rekey_crypto(new_key_bytes)

        # 2. Iterate over all entries in the underlying DiskStore cache
        # DiskStore stores compound keys as collection::key
        cache = cast(Any, self._app_store.kv)._cache
        # Collect all keys first to avoid iterating while modifying
        all_compound_keys = list(cache.iterkeys())

        # Perform in-place re-encryption
        reencrypted_count = 0
        for comp_key in all_compound_keys:
            try:
                collection, key = uncompound_key(comp_key)
            except Exception:
                continue

            if collection == "config" or key == "__index__":
                continue

            # Retrieve and decrypt the entry
            val = await self._app_store.kv.get(key, collection=collection)
            if val is not None and "data" in val:
                ciphertext = val["data"]
                # Decrypt with old crypto and re-encrypt with new crypto
                plaintext = old_crypto.decrypt(ciphertext)
                new_ciphertext = new_crypto.encrypt(plaintext)
                # Store the re-encrypted value back
                await self._app_store.kv.put(key, {"data": new_ciphertext}, collection=collection)
                reencrypted_count += 1

        # 3. Swap the key file or keyring entry
        if old_crypto.source_id == "local_key":
            if self._master_key_path is None:
                raise ValueError("master_key_path is required for 'local_key' mode")

            # Atomic swap of master key file
            temp_path = self._master_key_path.with_suffix(".tmp")
            key_data = {
                "version": 1,
                "key": base64.b64encode(new_key_bytes).decode("ascii"),
                "algorithm": "AES-256-GCM",
                "note": "Local master key for authsome. Protect this file.",
            }
            temp_path.write_text(json.dumps(key_data, indent=2), encoding="utf-8")
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass

            # Replace old key file atomically
            temp_path.replace(self._master_key_path)

        elif old_crypto.source_id == "keyring":
            if kr is None:
                raise RuntimeError(
                    "The 'keyring' package is required for keyring mode. Install it with: pip install keyring"
                )

            key_b64_str = base64.b64encode(new_key_bytes).decode("ascii")
            try:
                kr.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, key_b64_str)
            except Exception as exc:
                raise RuntimeError(f"Failed to store new master key in OS keyring: {exc}") from exc
        else:
            raise ValueError(f"Vault rekey is unsupported for encryption source '{old_crypto.source_id}'")

        # 4. Clear the active crypto in memory so it reloads on next access
        self._crypto = None
        logger.info("Rekey completed successfully. Re-encrypted {} keys.", reencrypted_count)

    async def close(self) -> None:
        """Release resources."""
        await self._app_store.close()

    async def __aenter__(self) -> Vault:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
