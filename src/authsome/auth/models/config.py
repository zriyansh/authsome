"""Authsome configuration helpers."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


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
