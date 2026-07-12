"""Browser-based live viewer: a websocket server (:mod:`metacsp.viz.server`)
feeding a prebuilt Vite/React frontend, replacing the dearpygui viewer.
Import-guarded behind the ``viz`` extra (``pip install metacsp[viz]``) so
the rest of ``metacsp`` works headless without ``starlette``/``uvicorn``
installed.
"""

from __future__ import annotations

try:
    import starlette  # noqa: F401
    import uvicorn  # noqa: F401
except ImportError as exc:  # pragma: no cover - exercised via tests/test_viz.py
    raise ImportError(
        "metacsp.viz requires the 'starlette' and 'uvicorn' packages. Install them with "
        "'pip install metacsp[viz]' to use the live viewer."
    ) from exc

from metacsp.viz.server import VizServer, serve

__all__ = ["VizServer", "serve"]
