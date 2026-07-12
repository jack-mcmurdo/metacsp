"""Thin dearpygui app/window bootstrap (M21, D10), reused by every live view
(:class:`~metacsp.viz.timeline.TimelineWindow` and future ones, e.g. a
geometry/trajectory canvas)."""

from __future__ import annotations

import dearpygui.dearpygui as dpg

__all__ = ["VizApp"]


class VizApp:
    """Owns one dearpygui context/viewport. Views (e.g. ``TimelineWindow``)
    are built inside it by calling their ``build()`` with this app.

    ``create()`` sets up the context and viewport but never shows it, so a
    headless caller (see ``tests/test_viz.py``) can build views and inspect
    them without opening an actual window; call :meth:`show` to display it
    and :meth:`run` to block on the render loop.
    """

    def __init__(self, title: str = "MetaCSP Viewer", width: int = 1200, height: int = 700) -> None:
        self.title = title
        self.width = width
        self.height = height
        self._created = False

    def create(self) -> None:
        if self._created:
            return
        dpg.create_context()
        dpg.create_viewport(title=self.title, width=self.width, height=self.height)
        dpg.setup_dearpygui()
        self._created = True

    def show(self) -> None:
        self.create()
        dpg.show_viewport()

    def render_frame(self) -> None:
        dpg.render_dearpygui_frame()

    def run(self) -> None:
        """Block, rendering frames, until the viewport is closed."""
        self.show()
        while dpg.is_dearpygui_running():
            self.render_frame()

    def destroy(self) -> None:
        if self._created:
            dpg.destroy_context()
            self._created = False
