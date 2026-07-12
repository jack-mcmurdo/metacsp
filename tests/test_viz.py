"""Tests for metacsp/viz/ (webviz M1: server + protocol v2).

Import-guard behavior (``metacsp.viz`` raises a clear ``ImportError`` when
``starlette``/``uvicorn`` are absent) is exercised by simulating absence via
``sys.modules`` -- this repo's dev environment always has them installed
(they are in the ``dev`` extra), so there is no other way to reach the
"absent" branch in CI.
"""

from __future__ import annotations

import importlib
import json
import sys

import pytest

pytest.importorskip("starlette")
pytest.importorskip("uvicorn")

from starlette.testclient import TestClient  # noqa: E402

from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver  # noqa: E402
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity  # noqa: E402
from metacsp.multi.allen_interval.allen_interval_constraint import (
    AllenIntervalConstraint,
)  # noqa: E402
from metacsp.time.bounds import Bounds  # noqa: E402
from metacsp.viz.server import VizServer  # noqa: E402

COMPONENT = "task"


def _make_activity(
    ans: ActivityNetworkSolver, symbol: str, est: int, duration: int
) -> SymbolicVariableActivity:
    act = ans.create_variable(COMPONENT)
    assert isinstance(act, SymbolicVariableActivity)
    act.set_symbolic_domain(symbol)
    release = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(est, est))
    release.from_ = act
    release.to = act
    assert ans.add_constraint(release)
    dur = AllenIntervalConstraint(AllenIntervalConstraint.Type.Duration, Bounds(duration, duration))
    dur.from_ = act
    dur.to = act
    assert ans.add_constraint(dur)
    return act


def _small_network() -> ActivityNetworkSolver:
    ans = ActivityNetworkSolver(0, 1_000_000, ["A", "B"])
    _make_activity(ans, "A", 0, 100)
    return ans


def test_viz_import_guard_when_starlette_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name in ("starlette", "uvicorn") or name.startswith(("starlette.", "uvicorn.")):
            monkeypatch.delitem(sys.modules, name, raising=False)
        if name == "metacsp.viz":
            monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, "starlette", None)

    with pytest.raises(ImportError, match="metacsp.viz requires"):
        importlib.import_module("metacsp.viz")


def test_snapshot_message_composition() -> None:
    ans = _small_network()
    server = VizServer(ans, [COMPONENT], period_ms=1_000_000)
    try:
        snapshot = server._build_snapshot()
        assert snapshot["kind"] == "snapshot"
        assert snapshot["seq"] == 1
        assert isinstance(snapshot["ts"], int)
        assert "variables" in snapshot and "constraints" in snapshot
        assert snapshot["envelopes"] == []
        timelines = snapshot["timelines"]
        assert len(timelines) == 1
        assert timelines[0]["component"] == COMPONENT
        non_none = [v for v in timelines[0]["values"] if v is not None]
        assert any("A" in v for v in non_none)
        json.dumps(snapshot)  # must be JSON-serializable

        second = server._build_snapshot()
        assert second["seq"] == 2  # seq is monotonic across messages
    finally:
        server.stop()


def test_websocket_roundtrip_sends_snapshot_then_delta_and_timelines() -> None:
    ans = _small_network()
    server = VizServer(ans, [COMPONENT], period_ms=1_000_000)
    try:
        with TestClient(server.app) as client:
            with client.websocket_connect("/ws") as ws:
                snapshot = ws.receive_json()
                assert snapshot["kind"] == "snapshot"
                first_seq = snapshot["seq"]

                _make_activity(ans, "B", 200, 100)  # variable_added + 2x constraint_added

                first_delta = ws.receive_json()
                assert first_delta["kind"] == "delta"
                assert first_delta["event"] == "variable_added"
                assert first_delta["seq"] > first_seq

                last_seq = first_delta["seq"]
                for _ in range(2):
                    delta = ws.receive_json()
                    assert delta["kind"] == "delta"
                    assert delta["event"] == "constraint_added"
                    assert delta["seq"] > last_seq
                    last_seq = delta["seq"]

                timelines_msg = ws.receive_json()
                assert timelines_msg["kind"] == "timelines"
                assert timelines_msg["seq"] > last_seq
                assert len(timelines_msg["timelines"]) == 1
    finally:
        server.stop()
