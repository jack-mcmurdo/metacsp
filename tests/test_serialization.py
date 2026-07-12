"""Tests for metacsp/serialization.py (M21)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from metacsp.meta.spatio_temporal.paths import TrajectoryEnvelopeScheduler
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope
from metacsp.serialization import (
    SnapshotPublisher,
    constraint_to_dict,
    network_to_dict,
    timeline_to_dict,
    trajectory_envelope_to_dict,
    variable_to_dict,
)
from metacsp.time.bounds import Bounds

COMPONENT = "task"
_DATA_DIR = Path(__file__).resolve().parent / "data" / "paths"


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
    _make_activity(ans, "B", 200, 100)
    ans.constraint_solvers[1].constraint_solvers[0].propagate()
    return ans


def test_variable_and_constraint_to_dict() -> None:
    ans = _small_network()
    variables = ans.constraint_network.get_variables()
    constraints = ans.constraint_network.get_constraints()
    assert variables and constraints

    vd = variable_to_dict(variables[0])
    assert set(vd) == {"id", "class", "domain"}
    assert vd["id"] == variables[0].id

    binary = [c for c in constraints if hasattr(c, "from_")]
    assert binary
    cd = constraint_to_dict(binary[0])
    assert set(cd) == {"class", "from", "to", "label"}
    assert cd["from"] == binary[0].from_.id
    assert cd["to"] == binary[0].to.id


def test_network_to_dict_round_trips_to_json() -> None:
    ans = _small_network()
    d = network_to_dict(ans.constraint_network)
    assert set(d) == {"variables", "constraints"}
    assert len(d["variables"]) == len(ans.constraint_network.get_variables())
    assert len(d["constraints"]) == len(ans.constraint_network.get_constraints())
    json.dumps(d)  # must be JSON-serializable


def test_timeline_to_dict() -> None:
    ans = _small_network()
    d = timeline_to_dict(ans, COMPONENT)
    assert d["component"] == COMPONENT
    # values[i] holds for the interval [pulses[i], pulses[i+1]); values has
    # the same length as pulses, with a trailing None (Timeline.java pads
    # its values array to match pulses -- see multi/activity/Timeline.java).
    assert len(d["values"]) == len(d["pulses"])
    assert d["values"][-1] is None
    # activity "A" holds in the first non-gap interval.
    non_none = [v for v in d["values"] if v is not None]
    assert any("A" in v for v in non_none)
    assert any("B" in v for v in non_none)
    json.dumps(d)


def test_trajectory_envelope_to_dict() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(1)
    assert vars_ is not None
    te = vars_[0]
    assert isinstance(te, TrajectoryEnvelope)
    te.set_footprint(1.3, 3.5, 0.0, 0.0)
    te.trajectory = Trajectory(str(_DATA_DIR / "path1.path"))
    te.robot_id = 1

    d = trajectory_envelope_to_dict(te)
    assert d["type"] == "Feature"
    assert d["geometry"]["type"] == "Polygon"
    assert d["properties"]["robot_id"] == 1
    assert d["properties"]["id"] == te.id
    json.dumps(d)


def test_snapshot_publisher_emits_delta_on_change() -> None:
    ans = ActivityNetworkSolver(0, 1_000_000, ["A"])
    messages: list[dict] = []
    publisher = SnapshotPublisher(
        ans, period_ms=1_000_000, callback=lambda s: messages.append(json.loads(s))
    )

    act = ans.create_variable(COMPONENT)
    assert isinstance(act, SymbolicVariableActivity)
    act.set_symbolic_domain("A")

    deltas = [m for m in messages if m["kind"] == "delta"]
    assert deltas
    assert deltas[0]["event"] == "variable_added"
    assert deltas[0]["variable"]["id"] == act.id
    publisher.teardown()


def test_snapshot_publisher_publishes_periodically() -> None:
    ans = _small_network()
    messages: list[dict] = []
    publisher = SnapshotPublisher(
        ans, period_ms=10, callback=lambda s: messages.append(json.loads(s))
    )
    publisher.start()
    try:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if any(m["kind"] == "snapshot" for m in messages):
                break
            time.sleep(0.01)
    finally:
        publisher.teardown()

    snapshots = [m for m in messages if m["kind"] == "snapshot"]
    assert snapshots
    assert "variables" in snapshots[0] and "constraints" in snapshots[0]
