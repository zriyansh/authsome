"""Global configuration models."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import Any

from pydantic import BaseModel, Field


def _major_version() -> int:
    try:
        return int(_pkg_version("authsome").split(".")[0])
    except (PackageNotFoundError, ValueError):
        return 1


class EncryptionConfig(BaseModel):
    """
    Encryption configuration block.

    Modes:
    - "auto":      env var → existing OS keyring key → local file (default)
    - "local_key": master key stored at ~/.authsome/master.key
    - "keyring":   master key stored in the OS keyring

    AUTHSOME_MASTER_KEY env var always takes precedence over any configured mode.
    """

    mode: str = "auto"


class GlobalConfig(BaseModel):
    """Global configuration stored in ~/.authsome/config.json."""

    spec_version: int = Field(default_factory=_major_version)
    default_profile: str = "default"
    encryption: EncryptionConfig | None = Field(default_factory=EncryptionConfig)

    extra_fields: dict[str, Any] = Field(default_factory=dict, exclude=True)

    model_config = {"extra": "allow"}
