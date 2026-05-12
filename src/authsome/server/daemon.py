"""Local daemon foreground runner."""

from __future__ import annotations

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7998


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, reload: bool = False) -> None:
    """Run the daemon in the foreground."""
    uvicorn.run(
        "authsome.server.app:create_app",
        host=host,
        port=port,
        log_level="info",
        reload=reload,
        factory=True,
        reload_includes=["*.py", "*.json", "*.html", "*.css", "*.js"],
    )
