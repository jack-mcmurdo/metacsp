"""Port of examples/meta/TestTrajectoryEnvelopeSchedulerThree.java.

The Java original resolves path files relative to the working directory
(``paths/newpath1.path``); here they are resolved relative to this repo's
``tests/data/paths/`` fixtures, per the same precedent as
``test_trajectory_envelope_scheduler.py``.

The Java original draws the constraint network with
``JTSDrawingPanel.drawConstraintNetwork``/``ConstraintNetwork.draw`` before
and after refinement (Swing, ``utility/UI`` -- not ported, see D10); those
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
    vars_ = solver.create_variables(3)
    assert vars_ is not None
    var0, var1, var2 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)
    assert isinstance(var2, TrajectoryEnvelope)

    traj0 = Trajectory(str(_DATA_DIR / "newpath1.path"))
    var0.set_footprint(1.3, 3.5, 0.0, 0.0)
    var0.trajectory = traj0

    traj1 = Trajectory(str(_DATA_DIR / "newpath2.path"))
    var1.set_footprint(1.3, 3.5, 0.0, 0.0)
    var1.trajectory = traj1

    traj2 = Trajectory(str(_DATA_DIR / "newpath3.path"))
    var2.set_footprint(1.3, 3.5, 0.0, 0.0)
    var2.trajectory = traj2

    var0.robot_id = 1
    var1.robot_id = 2
    var2.robot_id = 3

    print(f"{var0} has domain {var0.domain}")
    print(f"{var1} has domain {var1.domain}")
    print(f"{var2} has domain {var2.domain}")

    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    refined1 = meta_solver.refine_trajectory_envelopes()
    print(f"REFINED 1: {refined1}")

    refined2 = meta_solver.refine_trajectory_envelopes()
    print(f"REFINED 2: {refined2}")

    print("====================\n== BEFORE SOLVING ==\n====================")
    print_info(var0)
    print_info(var1)
    print_info(var2)

    solved = meta_solver.backtrack()
    print(f"Solved? {solved}")
    if solved:
        print(f"Added resolvers:\n{meta_solver.get_added_resolvers()}")

    print("===================\n== AFTER SOLVING ==\n===================")
    print_info(var0)
    print_info(var1)
    print_info(var2)


if __name__ == "__main__":
    main()
