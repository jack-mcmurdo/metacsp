"""Live Gantt/timeline view (M21, D10): replaces
``utility/timelinePlotting/{TimelinePublisher,TimelineVisualizer}.java`` +
``utility/UI/PlotBoxTLSmall.java`` (Swing image rendering of a
``SymbolicTimeline``) with a dearpygui drawlist that redraws itself on every
D2 constraint-network change event, instead of encoding PNGs to a
background image-publishing thread. Not a 1:1 port -- D10 explicitly does
not require Swing-UI fidelity, only equivalent live behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dearpygui.dearpygui as dpg

from metacsp.meta.symbols_and_time.symbolic_timeline import SymbolicTimeline

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_network_change_event import ConstraintNetworkChangeEvent
    from metacsp.viz.app import VizApp

__all__ = ["TimelineWindow"]

# RGBA colors, keyed by SymbolicTimeline interval state.
_COLOR_GAP = (60, 60, 60, 255)  # is_undetermined: no activity holds
_COLOR_NORMAL = (70, 130, 180, 255)  # is_critical: exactly one symbol holds
_COLOR_OVERLAP = (218, 165, 32, 255)  # more than one symbol holds at once
_COLOR_INCONSISTENT = (200, 30, 30, 255)  # is_inconsistent: empty symbol set
_ROW_HEIGHT = 40
_PIXELS_PER_TIME_UNIT = 0.05


class TimelineWindow:
    """A live Gantt view of one row per *component*, each row built from
    that component's :class:`~metacsp.meta.symbols_and_time.symbolic_timeline
    .SymbolicTimeline` (pulses + the symbols holding between them)."""

    def __init__(
        self,
        constraint_network: ConstraintNetwork,
        components: list[str],
        title: str = "Timeline",
        width: int = 1000,
        markings_to_exclude: tuple[Any, ...] = (),
    ) -> None:
        self.constraint_network = constraint_network
        self.components = list(components)
        self.title = title
        self.width = width
        self.markings_to_exclude = markings_to_exclude
        self._window_tag = f"timeline_window_{id(self)}"
        self._drawlist_tag = f"{self._window_tag}_canvas"
        self._built = False
        self._attached = False

    def _timelines(self) -> list[SymbolicTimeline]:
        return [
            SymbolicTimeline(self.constraint_network, component, *self.markings_to_exclude)
            for component in self.components
        ]

    def build(self, app: VizApp | None = None) -> None:
        """Create the dearpygui window and drawlist, then draw the current
        state. Safe to call headlessly (no viewport shown)."""
        if app is not None:
            app.create()
        height = max(1, len(self.components)) * _ROW_HEIGHT + 20
        with dpg.window(label=self.title, tag=self._window_tag, width=self.width, height=height):
            dpg.add_drawlist(width=self.width - 16, height=height - 40, tag=self._drawlist_tag)
        self._built = True
        self.refresh()

    def attach(self) -> None:
        """Subscribe to the constraint network's D2 change-listener stream
        (see ``framework/ConstraintNetwork.add_change_listener``) so this
        view redraws itself on every add/remove."""
        if not self._attached:
            self.constraint_network.add_change_listener(self._on_change)
            self._attached = True

    def detach(self) -> None:
        if self._attached:
            self.constraint_network.remove_change_listener(self._on_change)
            self._attached = False

    def _on_change(self, event: ConstraintNetworkChangeEvent) -> None:
        self.refresh()

    def refresh(self) -> None:
        if not self._built:
            return
        dpg.delete_item(self._drawlist_tag, children_only=True)
        for row, tl in enumerate(self._timelines()):
            y0 = row * _ROW_HEIGHT
            dpg.draw_text(
                (2, y0 + 2),
                tl.component,
                color=(230, 230, 230, 255),
                size=13,
                parent=self._drawlist_tag,
            )
            for i in range(len(tl.pulses) - 1):
                x0 = tl.pulses[i] * _PIXELS_PER_TIME_UNIT
                x1 = tl.pulses[i + 1] * _PIXELS_PER_TIME_UNIT
                value = tl.values[i]
                if tl.is_undetermined(value):
                    color = _COLOR_GAP
                    label = ""
                elif tl.is_inconsistent(value):
                    color = _COLOR_INCONSISTENT
                    label = "/".join(value.strings)  # type: ignore[union-attr]
                elif tl.is_critical(value):
                    color = _COLOR_NORMAL
                    label = "/".join(value.strings)  # type: ignore[union-attr]
                else:
                    color = _COLOR_OVERLAP
                    label = "/".join(value.strings)  # type: ignore[union-attr]
                dpg.draw_rectangle(
                    (x0, y0 + 16),
                    (x1, y0 + _ROW_HEIGHT - 2),
                    color=color,
                    fill=color,
                    parent=self._drawlist_tag,
                )
                if label:
                    dpg.draw_text(
                        (x0 + 2, y0 + 18),
                        label,
                        color=(255, 255, 255, 255),
                        size=11,
                        parent=self._drawlist_tag,
                    )

    def destroy(self) -> None:
        self.detach()
        if self._built and dpg.does_item_exist(self._window_tag):
            dpg.delete_item(self._window_tag)
        self._built = False
