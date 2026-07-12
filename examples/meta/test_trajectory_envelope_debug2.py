"""Port of examples/meta/TestTrajectoryEnvelopeDebug2.java.

The Java original ends by opening a ``TrajectoryEnvelopeAnimator`` (Swing,
``utility/UI`` -- not ported, see D10); dropped here, keeping the
refinement/scheduling/printing logic. Paths resolved against this repo's
``tests/data/paths/debugPaths/`` fixtures, per the precedent in
``examples/meta/test_trajectory_envelope_scheduler_three.py``.

Corner order for ``set_footprint`` corrected from the Java original's
self-intersecting ``(backLeft, backRight, frontLeft, frontRight)`` to
``(backLeft, backRight, frontRight, frontLeft)`` -- see the docstring of
``test_trajectory_envelope_debug.py`` for why.
"""

from __future__ import annotations

from pathlib import Path

from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "paths" / "debugPaths"

# Footprint coordinates (reference point in (0,0), as in SemRob).
_FRONT_LEFT = (8.100, 4.125)
_FRONT_RIGHT = (8.100, -3.430)
_BACK_RIGHT = (-6.920, -3.430)
_BACK_LEFT = (-6.920, 4.125)


def main() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 10000000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(7)
    assert vars_ is not None
    var0, var1, var2, var3, var4, var5, var6 = vars_

    for i, var in enumerate((var0, var1, var2, var3, var4, var5)):
        assert isinstance(var, TrajectoryEnvelope)
        var.set_footprint(_BACK_LEFT, _BACK_RIGHT, _FRONT_RIGHT, _FRONT_LEFT)
        var.trajectory = Trajectory(str(_DATA_DIR / f"test{i}.path"))
        var.robot_id = 1

    assert isinstance(var6, TrajectoryEnvelope)
    var6.set_footprint(_BACK_LEFT, _BACK_RIGHT, _FRONT_RIGHT, _FRONT_LEFT)
    var6.trajectory = Trajectory(str(_DATA_DIR / "test0_1.path"))
    var6.robot_id = 2

    def meets(from_: TrajectoryEnvelope, to: TrajectoryEnvelope) -> AllenIntervalConstraint:
        con = AllenIntervalConstraint(AllenIntervalConstraint.Type.Meets)
        con.from_ = from_
        con.to = to
        return con

    print(
        solver.add_constraints(
            meets(var4, var5),
            meets(var5, var2),
            meets(var2, var1),
            meets(var1, var0),
            meets(var0, var3),
        )
    )

    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    refined1 = meta_solver.refine_trajectory_envelopes()
    print("REFINED:", refined1)

    solved = meta_solver.backtrack()
    print("Solved?", solved)
    if solved:
        print("Added resolvers:")
        print(meta_solver.get_added_resolvers())


if __name__ == "__main__":
    main()
