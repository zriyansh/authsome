"""Health and readiness routes."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends

from authsome import __version__
from authsome.auth import AuthService
from authsome.server.routes._deps import get_auth_service
from authsome.server.schemas import HealthResponse, ReadyResponse

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
            issues.append(f"config: spec_version mismatch (got {config.spec_version}, expected {expected_spec_version})")
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
        connected_count = sum(
            1 for p in conn_list for c in p.get("connections", []) if c.get("status") == "connected"
        )
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
            issues.append("vault: sqlite store failed integrity check")
            checks["integrity"] = "failed"
        else:
            checks["integrity"] = "ok"
    except Exception as exc:
        checks["vault"] = "failed"
        checks["integrity"] = "failed"
        issues.append(f"vault: {exc}")

    # 6. File Permissions & Key Age Check
    try:
        home = auth.app_store.home
        master_key_file = home / "master.key"
        checks["key_age"] = "ok" # Default to ok
        
        # Permissions only checked on posix
        def check_permissions(file_path: os.PathLike) -> bool:
            st = os.stat(file_path)
            return (st.st_mode & 0o077) == 0

        if master_key_file.exists():
            if not check_permissions(master_key_file):
                issues.append("master.key has world-readable permissions (must be 0600)")
                checks["file_permissions"] = "failed"
            
            # Check key age
            mtime = master_key_file.stat().st_mtime
            age_days = int((time.time() - mtime) / 86400)
            if age_days > 90:
                warnings.append(f"master.key has not been rotated in {age_days} days")
        
        store_db_file = home / "profiles" / auth.identity / "store.db"
        if store_db_file.exists():
            if not check_permissions(store_db_file):
                issues.append("store.db has world-readable permissions (must be 0600)")
                checks["file_permissions"] = "failed"
        
        if "file_permissions" not in checks:
            checks["file_permissions"] = "ok"
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
        enc_desc = f"Local Key ({auth.app_store.home / 'master.key'})"
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
