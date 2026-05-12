"""Local disk-backed implementation of the AppStore."""

from __future__ import annotations

from pathlib import Path

from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.stores.disk import DiskStore
from loguru import logger

from authsome.auth.models.config import GlobalConfig
from authsome.store.interfaces import AppStore


class LocalAppStore(AppStore):
    """Disk-backed AppStore using py-key-value-aio's DiskStore.

    All data lives inside a single ``kv_store/`` directory managed by
    diskcache.  Swapping to a remote backend (e.g. PostgresStore)
    requires only replacing the DiskStore constructor call.
    """

    def __init__(self, home_dir: Path) -> None:
        self._home = home_dir
        self._home.mkdir(parents=True, exist_ok=True)
        self._store = DiskStore(directory=str(self._home / "kv_store"))

    @property
    def home(self) -> Path:
        return self._home

    @property
    def kv(self) -> AsyncKeyValue:
        return self._store

    # ── Initialization ────────────────────────────────────────────────────

    async def ensure_initialized(self) -> None:
        if await self._store.get("version", collection="config") is not None:
            return
        await self._store.put("version", {"data": "1"}, collection="config")
        await self.save_config(GlobalConfig())

    async def is_healthy(self) -> bool:
        return True

    async def check_integrity(self) -> bool:
        return True

    # ── Config (unencrypted) ──────────────────────────────────────────────

    async def get_config(self) -> GlobalConfig:
        val = await self._store.get("global", collection="config")
        if not val:
            return GlobalConfig()
        try:
            return GlobalConfig.model_validate_json(val["data"])
        except Exception as exc:
            logger.warning("Failed to parse config, using defaults: {}", exc)
            return GlobalConfig()

    async def save_config(self, config: GlobalConfig) -> None:
        await self._store.put("global", {"data": config.model_dump_json(indent=2)}, collection="config")

    async def close(self) -> None:
        pass
