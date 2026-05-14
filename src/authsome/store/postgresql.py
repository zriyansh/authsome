"""PostgreSQL-backed implementation of the AppStore."""

from __future__ import annotations

from pathlib import Path

from authsome.store.local import LocalAppStore


class PostgresAppStore(LocalAppStore):
    """AppStore implementation backed by py-key-value's PostgreSQL store."""

    def __init__(self, home_dir: Path, url: str, table_name: str = "authsome_kv") -> None:
        try:
            from key_value.aio.stores.postgresql import PostgreSQLStore
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "Hosted mode requires py-key-value-aio[postgresql] and asyncpg to be installed."
            ) from exc

        self._home = home_dir
        self._home.mkdir(parents=True, exist_ok=True)
        self._server_home = self._home / "server"
        self._server_home.mkdir(parents=True, exist_ok=True)
        self._store = PostgreSQLStore(url=url, table_name=table_name)
