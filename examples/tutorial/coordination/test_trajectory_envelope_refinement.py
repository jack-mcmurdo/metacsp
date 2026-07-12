"""Port of coordination/TestTrajectoryEnvelopeRefinement.java from the
meta-csp-tutorial repo (M23).

The Java original draws the geometries before/after refinement
(``JTSDrawingPanel``, ``ConstraintNetwork.draw`` -- Swing, not ported, see
D10); dropped here, keeping the refinement/printing logic. Paths resolved
against this repo's ``tests/data/paths/`` fixtures, per the precedent set
in M22's ``examples/meta/test_trajectory_envelope_scheduler_three.py``.
"""

from __future__ import annotations

from pathlib import Path

from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope

_DATA_DIR = Path(__file__).resolve().parents[3] / "tests" / "data" / "paths"


def main() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(3)
    assert vars_ is not None
    var0, var1, var2 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)
    assert isinstance(var2, TrajectoryEnvelope)

    # Parking envelopes not created for simplicity.
    var0.component = "Robot1"
    var0.symbolic_variable_activity.set_symbolic_domain("Driving")
    var0.robot_id = 1

    var1.component = "Robot2"
    var1.symbolic_variable_activity.set_symbolic_domain("Driving")
    var1.robot_id = 2

    var2.component = "Robot3"
    var2.symbolic_variable_activity.set_symbolic_domain("Driving")
    var2.robot_id = 3

    var0.set_footprint(2.3, 6.5, 0.0, 0.0)
    var0.trajectory = Trajectory(str(_DATA_DIR / "newpath1.path"))

    var1.set_footprint(2.3, 6.5, 0.0, 0.0)
    var1.trajectory = Trajectory(str(_DATA_DIR / "newpath2.path"))

    var2.set_footprint(2.3, 6.5, 0.0, 0.0)
    var2.trajectory = Trajectory(str(_DATA_DIR / "newpath3.path"))

    # Create a meta-constraint of type Map (needed here because the
    # meta-solver does refinement).
    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    # Refine trajectory envelopes so that we get better granularity
    #  -- refinement divides envelopes in spatial overlap areas
    #  -- refinement preserves large envelopes where possible
    refined1 = meta_solver.refine_trajectory_envelopes()
    print(
        f"Refinement added {len(refined1.get_variables())} variables "
        f"and {len(refined1.get_constraints())} constraints"
    )

    # This should do nothing.
    refined2 = meta_solver.refine_trajectory_envelopes()
    print(
        f"Refinement added {len(refined2.get_variables())} variables "
        f"and {len(refined2.get_constraints())} constraints"
    )

    print("\n===================\n== VARIABLE INFO ==\n===================")
    print(f"\n{var0.info}")
    print(f"\n{var1.info}")
    print(f"\n{var2.info}")


if __name__ == "__main__":
    main()
