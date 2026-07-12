"""Port of examples/meta/TestTrajectoryEnvelopeSerialization.java.

Java object serialization is not ported; per C10,
``ConstraintNetwork.save``/``.load`` use ``pickle`` instead. The Java
original also opens a ``TrajectoryEnvelopeAnimator`` per save/load (Swing,
not ported, see D10); dropped here. Saves to a temporary directory rather
than the Java original's repo-relative ``savedConstraintNetworks/*.cn``, so
running this example doesn't litter the repo.

Corner order for ``set_footprint`` corrected from the Java original's
self-intersecting ``(backLeft, backRight, frontLeft, frontRight)`` to
``(backLeft, backRight, frontRight, frontLeft)`` -- see the docstring of
``test_trajectory_envelope_debug.py`` for why.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "paths"
_FRONT_LEFT = (1.8, 0.7)
_FRONT_RIGHT = (1.8, -0.7)
_BACK_RIGHT = (-1.8, -0.7)
_BACK_LEFT = (-1.8, 0.7)


def main() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(2)
    assert vars_ is not None
    var0, var1 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)

    var0.set_footprint(_BACK_LEFT, _BACK_RIGHT, _FRONT_RIGHT, _FRONT_LEFT)
    var0.trajectory = Trajectory(str(_DATA_DIR / "path1.path"))

    var1.set_footprint(_BACK_LEFT, _BACK_RIGHT, _FRONT_RIGHT, _FRONT_LEFT)
    var1.trajectory = Trajectory(str(_DATA_DIR / "path3.path"))

    var0.robot_id = 1
    var1.robot_id = 2

    print(f"{var0} has domain {var0.domain}")
    print(f"{var1} has domain {var1.domain}")

    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        before_path = tmp_path / "constraintNetworkBeforeSolving.pickle"
        solver.constraint_network.save(before_path)
        con_before = ConstraintNetwork.load(before_path)
        print(f"Before solving: {len(con_before.get_variables())} variables")

        refined1 = meta_solver.refine_trajectory_envelopes()
        print("REFINED:", refined1)

        solved = meta_solver.backtrack()
        print("Solved?", solved)
        if solved:
            print("Added resolvers:")
            print(meta_solver.get_added_resolvers())

        after_path = tmp_path / "constraintNetworkAfterSolving.pickle"
        solver.constraint_network.save(after_path)
        con_after = ConstraintNetwork.load(after_path)
        print(f"After solving: {len(con_after.get_variables())} variables")


if __name__ == "__main__":
    main()
