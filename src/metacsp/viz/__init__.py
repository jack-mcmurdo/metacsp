"""Live viewer (M21, D10): a dearpygui replacement for the Swing
``utility/UI`` package. Import-guarded behind the ``viz`` extra
(``pip install metacsp[viz]``) so the rest of ``metacsp`` works headless
without ``dearpygui`` installed.
"""

from __future__ import annotations

try:
    import dearpygui.dearpygui as _dpg  # noqa: F401
except ImportError as exc:  # pragma: no cover - exercised via tests/test_viz.py
    raise ImportError(
        "metacsp.viz requires the 'dearpygui' package. Install it with "
        "'pip install metacsp[viz]' (or 'pip install dearpygui') to use the live viewer."
    ) from exc

from metacsp.viz.app import VizApp
from metacsp.viz.timeline import TimelineWindow

__all__ = ["VizApp", "TimelineWindow"]
