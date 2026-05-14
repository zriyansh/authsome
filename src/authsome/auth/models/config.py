"""Global configuration models."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal

from pydantic import BaseModel, Field


def current_spec_version() -> int:
    """Return the config spec version derived from authsome's minor package version."""
    try:
        package_version = version("authsome")
    except PackageNotFoundError:
        return 0
    parts = package_version.split(".")
    if len(parts) < 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


class EncryptionConfig(BaseModel):
    """
    Encryption configuration block.

    Modes:
    - "local_key": master key stored at ~/.authsome/server/master.key
    - "keyring":   master key stored in the OS keyring
    """

    mode: str = "local_key"


class ProxyConfig(BaseModel):
    """Proxy configuration block."""

    mode: Literal[
        "connected_allow",
        "connected_deny",
        "configured_allow",
        "configured_deny",
    ] = "connected_allow"


class GlobalConfig(BaseModel):
    """Daemon configuration for the local Authsome install."""

    spec_version: int = Field(default_factory=current_spec_version)
    encryption: EncryptionConfig | None = Field(default_factory=EncryptionConfig)
    proxy: ProxyConfig | None = Field(default_factory=ProxyConfig)

    extra_fields: dict[str, Any] = Field(default_factory=dict, exclude=True)

    model_config = {"extra": "allow"}
