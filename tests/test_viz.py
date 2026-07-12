"""Tests for metacsp/viz/ (M21).

Import-guard behavior (``metacsp.viz`` raises a clear ``ImportError`` when
``dearpygui`` is absent) is exercised by simulating absence via
``sys.modules`` -- this repo's dev environment always has ``dearpygui``
installed (it is in the ``dev`` extra), so there is no other way to reach
the "absent" branch in CI. When ``dearpygui`` is genuinely present (the
normal case), a ``TimelineWindow`` is built headlessly: a context is
created but the viewport is never shown, matching PLAN.md's M21 acceptance
criterion.
"""

from __future__ import annotations

import importlib
import sys

import pytest

pytest.importorskip("dearpygui")


def test_viz_import_guard_when_dearpygui_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name == "dearpygui" or name.startswith("dearpygui.") or name == "metacsp.viz":
            monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, "dearpygui", None)
    monkeypatch.setitem(sys.modules, "dearpygui.dearpygui", None)

    with pytest.raises(ImportError, match="metacsp.viz requires"):
        importlib.import_module("metacsp.viz")


def test_timeline_window_builds_headlessly() -> None:
    # Re-import normally (the guard test above may have poisoned sys.modules
    # entries, but monkeypatch undoes that on teardown).
    from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.viz.app import VizApp
    from metacsp.viz.timeline import TimelineWindow

    ans = ActivityNetworkSolver(0, 1_000_000, ["A"])
    act = ans.create_variable("task")
    assert isinstance(act, SymbolicVariableActivity)
    act.set_symbolic_domain("A")

    app = VizApp(title="test", width=400, height=200)
    window = TimelineWindow(ans.constraint_network, ["task"], title="test-timeline")
    try:
        app.create()  # context + viewport, but no show_viewport()
        window.build(app)
        window.attach()
        window.refresh()
    finally:
        window.destroy()
        app.destroy()
