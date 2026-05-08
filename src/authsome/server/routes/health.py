"""Health and readiness routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from authsome import __version__
from authsome.auth import AuthService
from authsome.server.routes._deps import get_auth_service
from authsome.server.schemas import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, pid=os.getpid())


def _check_config(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        config = auth.app_store.get_config()
        checks["config"] = "ok" if config else "ok"
    except Exception as exc:
        checks["config"] = "failed"
        issues.append(f"config: {exc}")


def _check_providers(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        auth.list_providers()
        checks["providers"] = "ok"
    except Exception as exc:
        checks["providers"] = "failed"
        issues.append(f"providers: {exc}")


def _check_vault(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        auth.vault.put("__ready_test__", "ok", profile=auth.identity)
        value = auth.vault.get("__ready_test__", profile=auth.identity)
        auth.vault.delete("__ready_test__", profile=auth.identity)
        checks["vault"] = "ok" if value == "ok" else "failed"
        if value != "ok":
            issues.append("vault: readiness roundtrip failed")
    except Exception as exc:
        checks["vault"] = "failed"
        issues.append(f"vault: {exc}")


def _check_permissions(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        if os.name != "nt":
            master_key_path = auth.app_store.home / "master.key"
            if master_key_path.exists():
                mode = master_key_path.stat().st_mode
                if (mode & 0o077) != 0:
                    checks["permissions"] = "failed"
                    issues.append(
                        f"permissions: master.key has insecure permissions {oct(mode & 0o777)} (expected 0600)"
                    )

            db_path = auth.app_store.home / "profiles" / auth.identity / "store.db"
            if db_path.exists():
                mode = db_path.stat().st_mode
                if (mode & 0o077) != 0:
                    checks["permissions"] = "failed"
                    issues.append(f"permissions: store.db has insecure permissions {oct(mode & 0o777)} (expected 0600)")

            if "permissions" not in checks:
                checks["permissions"] = "ok"
        else:
            checks["permissions"] = "ok"
    except Exception as exc:
        checks["permissions"] = "failed"
        issues.append(f"permissions: {exc}")


def _check_profiles(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        auth.app_store.list_profiles()
        checks["profiles"] = "ok"
    except Exception as exc:
        checks["profiles"] = "failed"
        issues.append(f"profiles: {exc}")


def _check_connections(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        connections = auth.list_connections()
        has_active = any(conn.get("status") == "connected" for p in connections for conn in p.get("connections", []))
        checks["connections"] = "ok"
        if not has_active:
            issues.append("warning: No providers have active connections")
    except Exception as exc:
        checks["connections"] = "failed"
        issues.append(f"connections: {exc}")


def _check_key_age(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        master_key_path = auth.app_store.home / "master.key"
        if master_key_path.exists():
            from datetime import UTC, datetime

            from authsome.utils import utc_now

            mtime = datetime.fromtimestamp(master_key_path.stat().st_mtime, tz=UTC)
            age_days = (utc_now() - mtime).days
            if age_days > 90:
                checks["key_age"] = "warn"
                issues.append(f"warning: master.key has not been rotated in >90 days (age: {age_days} days)")
            else:
                checks["key_age"] = "ok"
        else:
            checks["key_age"] = "ok"
    except Exception as exc:
        checks["key_age"] = "failed"
        issues.append(f"key_age: {exc}")


def _check_integrity(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        import sqlite3

        db_path = auth.app_store.home / "profiles" / auth.identity / "store.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            try:
                cursor = conn.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()
                if result and result[0] == "ok":
                    checks["integrity"] = "ok"
                else:
                    checks["integrity"] = "failed"
                    issues.append(f"integrity: PRAGMA integrity_check failed on store.db: {result}")
            finally:
                conn.close()
        else:
            checks["integrity"] = "ok"
    except Exception as exc:
        checks["integrity"] = "failed"
        issues.append(f"integrity: {exc}")


def _check_version_compatibility(auth: AuthService, checks: dict[str, str], issues: list[str]) -> None:
    try:
        checks["version_compatibility"] = "ok"
        version_path = auth.app_store.home / "version"
        if version_path.exists():
            v = version_path.read_text(encoding="utf-8").strip()
            if v != "2":
                checks["version_compatibility"] = "failed"
                issues.append(f"version_compatibility: Home version is {v} but expected 2")
    except Exception as exc:
        checks["version_compatibility"] = "failed"
        issues.append(f"version_compatibility: {exc}")


@router.get("/ready", response_model=ReadyResponse)
def ready(auth: AuthService = Depends(get_auth_service)) -> ReadyResponse:
    checks: dict[str, str] = {}
    issues: list[str] = []

    _check_config(auth, checks, issues)
    _check_providers(auth, checks, issues)
    _check_vault(auth, checks, issues)
    _check_permissions(auth, checks, issues)
    _check_profiles(auth, checks, issues)
    _check_connections(auth, checks, issues)
    _check_key_age(auth, checks, issues)
    _check_integrity(auth, checks, issues)
    _check_version_compatibility(auth, checks, issues)

    has_critical_failures = any(not issue.startswith("warning:") for issue in issues)
    return ReadyResponse(status="ready" if not has_critical_failures else "not_ready", checks=checks, issues=issues)


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
