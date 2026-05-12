"""Unified storage interfaces for Authsome.

The AppStore handles bootstrapping (config and initialization) and
exposes the underlying async KV backend for the Vault to wrap with
encryption.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from key_value.aio.protocols.key_value import AsyncKeyValue

if TYPE_CHECKING:
    from authsome.auth.models.config import GlobalConfig


class AppStore(ABC):
    """Storage backend — config + raw async KV access."""

    @property
    @abstractmethod
    def home(self) -> Path:
        """Base directory for this storage system."""
        ...

    @property
    @abstractmethod
    def kv(self) -> AsyncKeyValue:
        """The underlying async key-value store."""
        ...

    # ── Initialization ────────────────────────────────────────────────────

    @abstractmethod
    def ensure_initialized(self) -> None:
        """Seed the store with version marker and default config."""
        ...

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if the store is accessible."""
        ...

    # ── Config (unencrypted — needed before crypto is available) ──────────

    @abstractmethod
    def get_config(self) -> GlobalConfig:
        """Get global configuration."""
        ...

    @abstractmethod
    def save_config(self, config: GlobalConfig) -> None:
        """Save global configuration."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close all underlying storage connections."""
        ...
