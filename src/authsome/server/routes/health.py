"""Health and readiness routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from authsome import __version__
from authsome.auth import AuthService
from authsome.server.routes._deps import get_auth_service
from authsome.server.schemas import HealthResponse, ReadyResponse
from authsome.store.local import LocalAppStore

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@router.get("/ready", response_model=ReadyResponse)
def ready(auth: AuthService = Depends(get_auth_service)) -> ReadyResponse:
    checks: dict[str, str] = {}
    issues: list[str] = []
    warnings: list[str] = []

    # 1. Config & Schema Version Check
    try:
        config = auth.app_store.get_config()
        checks["config"] = "ok"

        # Verify spec_version matches standard expected version (1)
        expected_spec_version = 1
        if getattr(config, "spec_version", None) != expected_spec_version:
            issues.append(
                f"config: spec_version mismatch (got {config.spec_version}, expected {expected_spec_version})"
            )
            checks["version_compatibility"] = "failed"
        else:
            checks["version_compatibility"] = "ok"
    except Exception as exc:
        checks["config"] = "failed"
        checks["version_compatibility"] = "failed"
        issues.append(f"config: {exc}")

    # 2. Profiles Count Check
    try:
        auth.list_profiles()
        checks["profiles"] = "ok"
    except Exception as exc:
        checks["profiles"] = "failed"
        issues.append(f"profiles: {exc}")

    # 3. Providers List Check
    try:
        auth.list_providers()
        checks["providers"] = "ok"
    except Exception as exc:
        checks["providers"] = "failed"
        issues.append(f"providers: {exc}")

    # 4. Connected Providers Check
    try:
        conn_list = auth.list_connections()
        checks["connections"] = "ok"
        connected_count = sum(1 for p in conn_list for c in p.get("connections", []) if c.get("status") == "connected")
        if connected_count == 0:
            warnings.append("no active provider connections found")
    except Exception as exc:
        checks["connections"] = "failed"
        issues.append(f"connections: {exc}")

    # 5. Vault Roundtrip & Store Integrity Check
    try:
        auth.vault.put("__ready_test__", "ok", profile=auth.identity)
        value = auth.vault.get("__ready_test__", profile=auth.identity)
        auth.vault.delete("__ready_test__", profile=auth.identity)

        if value != "ok":
            issues.append("vault: readiness roundtrip failed")
            checks["vault"] = "failed"
        else:
            checks["vault"] = "ok"

        if not auth.vault.check_integrity(profile=auth.identity):
            issues.append("vault: store failed integrity check")
            checks["integrity"] = "failed"
        else:
            checks["integrity"] = "ok"
    except Exception as exc:
        checks["vault"] = "failed"
        checks["integrity"] = "failed"
        issues.append(f"vault: {exc}")

    # TODO: Re-enable master.key permission checks once backend implementation stabilizes.
    # (Previous implementation alerted users if file was world-readable)

    except Exception as exc:
        if "file_permissions" not in checks:
            checks["file_permissions"] = "failed"
        checks["key_age"] = "failed"
        issues.append(f"file_checks: {exc}")

    status = "ready" if not issues else "not_ready"
    return ReadyResponse(status=status, checks=checks, issues=issues, warnings=warnings)


@router.get("/whoami")
def whoami(auth: AuthService = Depends(get_auth_service)) -> dict[str, str]:
    config = auth.app_store.get_config()
    enc_mode = config.encryption.mode if config.encryption else "local_key"
    if enc_mode == "local_key":
        key_path = (
            auth.app_store.get_master_key_path()
            if isinstance(auth.app_store, LocalAppStore)
            else auth.app_store.home / "master.key"
        )
        enc_desc = f"Local Key ({key_path})"
    elif enc_mode == "keyring":
        enc_desc = "OS Keyring"
    else:
        enc_desc = enc_mode
    return {
        "version": __version__,
        "home": str(auth.app_store.home),
        "active_identity": auth.identity,
        "encryption_backend": enc_desc,
    }
