"""Port of examples/meta/TestTrajectoryEnvelopeScheduler.java.

The Java original resolves path files relative to the working directory
(``paths/path1.path``); here they are resolved relative to this repo's
``tests/data/paths/`` fixtures (the same files, copied from the Java repo's
``paths/`` directory per PLAN.md), following the precedent set by
``examples/multi/test_spatio_temporal_variable_solver_overlaps_intersects.py``
(M14).

The Java original draws the constraint network (``ConstraintNetwork.draw``),
sleeps 10s, then builds a ``TrajectoryEnvelopeAnimator`` and draws the
variable hierarchy (all Swing, ``utility/UI`` -- not ported, see D10); those
calls are dropped here, keeping the scheduling/printing logic.
"""

from __future__ import annotations

from pathlib import Path

from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "paths"


def print_info(te: TrajectoryEnvelope) -> None:
    assert te.trajectory is not None
    te_dts = te.trajectory.dts
    te_cts = te.cts
    print(
        "------------------------------------------\n"
        f"{te}\nGround env: {te.ground_envelopes}\nDTs and CTs\n"
        "------------------------------------------"
    )
    for i, dt in enumerate(te_dts):
        print(f"{i}: {dt:.2f} \t {te_cts[i]:.2f}")


def main() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(2)
    assert vars_ is not None
    var0, var1 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)

    traj0 = Trajectory(str(_DATA_DIR / "path1.path"))
    var0.set_footprint(1.3, 3.5, 0.0, 0.0)
    var0.trajectory = traj0

    traj1 = Trajectory(str(_DATA_DIR / "path3.path"))
    var1.set_footprint(1.3, 3.5, 0.0, 0.0)
    var1.trajectory = traj1

    var0.robot_id = 1
    var1.robot_id = 2

    print(f"{var0} has domain {var0.domain}")
    print(f"{var1} has domain {var1.domain}")

    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    refined1 = meta_solver.refine_trajectory_envelopes()
    print(f"REFINED 1: {refined1}")

    print("====================\n== BEFORE SOLVING ==\n====================")
    print_info(var0)
    print_info(var1)

    solved = meta_solver.backtrack()
    print(f"Solved? {solved}")
    if solved:
        print(f"Added resolvers:\n{meta_solver.get_added_resolvers()}")

    print("===================\n== AFTER SOLVING ==\n===================")
    print_info(var0)
    print_info(var1)


if __name__ == "__main__":
    main()
