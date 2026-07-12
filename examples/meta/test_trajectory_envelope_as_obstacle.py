"""Port of examples/meta/TestTrajectoryEnvelopeAsObstacle.java.

The Java original ends by opening a ``TrajectoryEnvelopeAnimator`` with
markers and an extra geofence polygon (Swing, ``utility/UI`` -- not ported,
see D10); dropped here, keeping the refinement/scheduling/printing logic
(the geofence polygon itself is only ever used as a marker on that dropped
animator, so it is not constructed either). Paths resolved against this
repo's ``tests/data/paths/`` fixtures, per the precedent in
``examples/meta/test_trajectory_envelope_scheduler_three.py``.
"""

from __future__ import annotations

from pathlib import Path

from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatio_temporal.paths import Pose, Trajectory, TrajectoryEnvelope
from metacsp.time.bounds import Bounds

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "paths"


def main() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(4)
    assert vars_ is not None
    var0, var1, var2, var3 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)
    assert isinstance(var2, TrajectoryEnvelope)
    assert isinstance(var3, TrajectoryEnvelope)

    var0.set_footprint(1.3, 3.5, 0.0, 0.0)
    var0.trajectory = Trajectory(str(_DATA_DIR / "newpath1.path"))

    var1.set_footprint(1.3, 3.5, 0.0, 0.0)
    var1.trajectory = Trajectory(str(_DATA_DIR / "newpath2.path"))

    var2.set_footprint(1.3, 3.5, 0.0, 0.0)
    var2.trajectory = Trajectory(str(_DATA_DIR / "newpath3.path"))

    # This is an obstacle!
    var3.set_footprint(1, 1, 0, 0)
    obs_position = Pose(-10, -2, 0.0)
    var3.trajectory = Trajectory([obs_position])
    var3.refinable = False

    # When the obstacle should appear.
    obstacle_release = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Release, Bounds(5000, 5000)
    )
    obstacle_release.from_ = var3
    obstacle_release.to = var3
    obstacle_deadline = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Deadline, Bounds(solver.horizon, solver.horizon)
    )
    obstacle_deadline.from_ = var3
    obstacle_deadline.to = var3
    solver.add_constraints(obstacle_release, obstacle_deadline)

    var0.robot_id = 1
    var1.robot_id = 2
    var2.robot_id = 3

    print(f"{var0} has domain {var0.domain}")
    print(f"{var1} has domain {var1.domain}")
    print(f"{var2} has domain {var2.domain}")
    print(f"{var3} has domain {var3.domain}")

    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    refined1 = meta_solver.refine_trajectory_envelopes()
    print("REFINED 1:", refined1)

    refined2 = meta_solver.refine_trajectory_envelopes()
    print("REFINED 2:", refined2)

    solved = meta_solver.backtrack()
    print("Solved?", solved)
    if solved:
        print("Added resolvers:")
        print(meta_solver.get_added_resolvers())


if __name__ == "__main__":
    main()
