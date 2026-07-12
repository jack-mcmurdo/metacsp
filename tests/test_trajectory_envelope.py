"""Tests for metacsp.multi.spatio_temporal(.paths): Pose/PoseSteering/
Trajectory/TrajectoryEnvelope/TrajectoryEnvelopeSolver (M14).

TestPoseClass.java's assertions are ported separately in test_pose.py. The
Java example this module partly exercises,
TestSpatioTemporalVariableSolverOverlapsIntersects.java, is a ``main()``
demo with no JUnit assertions of its own (only prints); the one condition
it does check -- ``solver.addConstraints(...)`` -- is asserted below
(test_release_deadline_narrower_than_duration_fails_to_add), using the same
kind of Release/Deadline-vs-Duration conflict the example's constants
produce. The envelope polygon areas and temporal bounds below are computed
deterministically by running our own port against the ``path1.path``/
``path3.path`` fixtures (copied from the Java repo's ``paths/`` directory
per PLAN.md) -- there is no Java assertion oracle for the specific numeric
values, only for the general shape of the computation (a rectangular
footprint swept along the path, unioned via convex hulls, as coded in
TrajectoryEnvelope.java).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from metacsp.multi.allen_interval import AllenIntervalConstraint
from metacsp.multi.spatio_temporal.paths import (
    Pose,
    PoseSteering,
    Trajectory,
    TrajectoryEnvelope,
    TrajectoryEnvelopeSolver,
)
from metacsp.time.bounds import Bounds

_DATA_DIR = Path(__file__).resolve().parent / "data" / "paths"

# A simple 2x1m rectangular footprint, reference point at the origin.
_FOOTPRINT = ((1.0, -0.5), (1.0, 0.5), (-1.0, 0.5), (-1.0, -0.5))


def _make_solver() -> TrajectoryEnvelopeSolver:
    return TrajectoryEnvelopeSolver(0, 1_000_000)


def test_trajectory_loaded_from_fixture_file() -> None:
    traj = Trajectory(str(_DATA_DIR / "path1.path"))
    # path1.path has 52 lines, each a "x y theta steering" pose.
    assert len(traj.pose_steering) == 52
    assert traj.sequence_number_start == 0
    assert traj.sequence_number_end == 51
    # dts[0] is always 0 (no time elapses "arriving" at the first pose).
    assert traj.dts[0] == 0.0
    assert len(traj.dts) == 52
    # The (simulated) time profile sums to the same total travel time
    # baked into the fixture's implicit "arrival at last pose" moment.
    assert sum(traj.dts) == pytest.approx(21.0, abs=0.1)
    assert traj.path_length == pytest.approx(35.80188, abs=1e-3)


def test_trajectory_envelope_polygon_area_and_temporal_bounds() -> None:
    solver = _make_solver()
    te = solver.create_envelope_no_parking(1, str(_DATA_DIR / "path1.path"), "Driving", *_FOOTPRINT)
    assert isinstance(te, TrajectoryEnvelope)

    # Path length (number of poses) matches the fixture's line count.
    assert te.path_length == 52
    assert te.sequence_number_start == 0
    assert te.sequence_number_end == 51

    # No other temporal constraints were added, so the envelope's placement
    # is pinned only by its Duration constraint (from RESOLUTION=1000 *
    # Trajectory.dts) at the temporal origin.
    tv = te.temporal_variable
    assert tv.est == 0
    assert tv.eet == 20990

    # The spatial envelope: footprint swept along the path, unioned via
    # convex hulls between successive footprints (TrajectoryEnvelope.java's
    # createEnvelope()).
    geom = te.envelope_variable.domain.geometry
    assert geom.is_valid
    assert geom.area == pytest.approx(39.16236, abs=1e-3)
    # Sanity: the envelope is strictly larger than a single footprint
    # instance (2 m^2) since the robot moves along a nontrivial path.
    assert geom.area > 2.0


def test_trajectory_envelope_reference_path_is_line_string() -> None:
    solver = _make_solver()
    te = solver.create_envelope_no_parking(1, str(_DATA_DIR / "path3.path"), "Driving", *_FOOTPRINT)
    assert te.path_length == 29
    ref_geom = te.reference_path_variable.domain.geometry
    assert ref_geom.geom_type == "LineString"
    assert len(list(ref_geom.coords)) == 29


def test_single_pose_trajectory_envelope_is_a_point() -> None:
    solver = _make_solver()
    te = solver.create_envelope_no_parking(
        1, [PoseSteering(0.0, 0.0, 0.0, 0.0)], "Parking", *_FOOTPRINT
    )
    assert te.path_length == 1
    ref_geom = te.reference_path_variable.domain.geometry
    assert ref_geom.geom_type == "Point"
    # A single-footprint envelope: its area equals exactly one footprint.
    geom = te.envelope_variable.domain.geometry
    assert geom.area == pytest.approx(2.0, abs=1e-9)


def test_release_deadline_narrower_than_duration_fails_to_add() -> None:
    """Port of the one condition TestSpatioTemporalVariableSolverOverlaps
    Intersects.java's main() checks: ``solver.addConstraints(...)``.

    The example pins Release/Deadline windows of only 10-20ms and 15-25ms
    on two envelopes whose minimum Duration (from their trajectories'
    temporal profiles) is on the order of tens of thousands of
    milliseconds -- an infeasible combination, so addConstraints must
    return False, exactly as in the Java example.
    """
    solver = _make_solver()
    var0 = solver.create_envelope_no_parking(
        0, str(_DATA_DIR / "path1.path"), "Driving", *_FOOTPRINT
    )
    var1 = solver.create_envelope_no_parking(
        1, str(_DATA_DIR / "path3.path"), "Driving", *_FOOTPRINT
    )

    rel_var0 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(10, 10))
    rel_var0.from_ = var0
    rel_var0.to = var0

    dead_var0 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Deadline, Bounds(20, 20))
    dead_var0.from_ = var0
    dead_var0.to = var0

    rel_var1 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(15, 15))
    rel_var1.from_ = var1
    rel_var1.to = var1

    dead_var1 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Deadline, Bounds(25, 25))
    dead_var1.from_ = var1
    dead_var1.to = var1

    assert solver.add_constraints(rel_var0, rel_var1, dead_var0, dead_var1) is False


def test_create_envelopes_default_footprint_and_parking() -> None:
    # DEFAULT_FOOTPRINT is deliberately *not* exercised here: its coordinate
    # order is copied verbatim from the Java source (see the class
    # docstring) and traces a self-intersecting quadrilateral, which GEOS
    # (like JTS, whose "side location conflict" TopologyException message
    # it shares verbatim -- D4) refuses to union. An explicit, valid
    # footprint is used instead to test create_envelopes()'s actual
    # envelope/parking-wrapping logic without tripping that latent upstream
    # bug.
    solver = _make_solver()
    traj = Trajectory(str(_DATA_DIR / "path1.path"))
    envelopes_by_robot = solver.create_envelopes(5, traj, footprint=_FOOTPRINT)
    assert set(envelopes_by_robot.keys()) == {5}
    parking_start, driving, parking_end = envelopes_by_robot[5]
    assert parking_start.robot_id == 5
    assert driving.robot_id == 5
    assert parking_end.robot_id == 5
    assert parking_start.path_length == 1
    assert parking_end.path_length == 1
    assert driving.path_length == 52
    assert parking_start.refinable is False
    assert parking_end.refinable is False
    assert driving.symbols == ["Driving"]
    assert parking_start.symbols == ["Parking (initial)"]
    assert parking_end.symbols == ["Parking (final)"]


def test_pose_steering_interpolate() -> None:
    p1 = PoseSteering(0.0, 0.0, 0.0, 0.0)
    p2 = PoseSteering(10.0, 0.0, 0.0, 0.0)
    mid = p1.interpolate(p2, 0.5)
    assert mid.x == pytest.approx(5.0)
    assert mid.y == pytest.approx(0.0)


def test_trajectory_envelope_requires_footprint_before_trajectory() -> None:
    from metacsp.exceptions import NoFootprintException

    solver = _make_solver()
    variables = solver.create_variables(1)
    assert variables is not None
    te = variables[0]
    assert isinstance(te, TrajectoryEnvelope)
    traj = Trajectory([Pose(0.0, 0.0, 0.0)])
    with pytest.raises(NoFootprintException):
        te.trajectory = traj
