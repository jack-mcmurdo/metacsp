"""Port of coordination/TestTrajectoryEnvelopeControl.java from the
meta-csp-tutorial repo (M23).

The Java original draws the geometries/constraint networks and opens a
``TrajectoryEnvelopeAnimator`` (``JTSDrawingPanel``, ``ConstraintNetwork
.draw``, ``utility/UI`` -- Swing, not ported, see D10); dropped here,
keeping the refinement/scheduling/dispatching logic. Paths resolved
against this repo's ``tests/data/paths/`` fixtures, per the precedent set
in M22's ``examples/meta/test_trajectory_envelope_scheduler_three.py``.

The Java original's Swing GUI keeps its JVM alive indefinitely with no
explicit wait; since none of that UI is ported and D9 dispatch/animator
threads are daemon threads, this port runs the dispatcher for a bounded
number of seconds (long enough to see "Dispatched"/"Finished" activity
prints) instead of hanging forever, per the precedent set in M22's
``examples/meta/test_constraint_network_animator.py``.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from metacsp.dispatching.dispatching_function import DispatchingFunction
from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

_DATA_DIR = Path(__file__).resolve().parents[3] / "tests" / "data" / "paths"

_WIDTH = 2.3
_LENGTH = 6.5
_PARKING_DURATION = 3000
_NUM_ROBOTS = 3
_RUN_SECONDS = 5.0


class _RobotDispatchingFunction(DispatchingFunction):
    def __init__(self, component: str, animator: ConstraintNetworkAnimator) -> None:
        super().__init__(component)
        self._animator = animator

    def skip(self, act: SymbolicVariableActivity) -> bool:
        return "Parking" in act.symbols[0]

    def dispatch(self, act: SymbolicVariableActivity) -> None:
        print(">>>> Dispatched", act)

        def ideal_controller() -> None:
            while self._animator.time_now < act.temporal_variable.eet:
                time.sleep(0.01)
            print("<<<< Finished", act)
            self.finish(act)

        threading.Thread(target=ideal_controller, daemon=True).start()


def main() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(3 * _NUM_ROBOTS)
    assert vars_ is not None

    for i in range(_NUM_ROBOTS):
        driving = vars_[i]
        assert isinstance(driving, TrajectoryEnvelope)
        driving.component = f"Robot{i}"
        driving.symbolic_variable_activity.set_symbolic_domain("Driving")
        driving.robot_id = i
        driving.set_footprint(_WIDTH, _LENGTH, 0.0, 0.0)
        driving.trajectory = Trajectory(str(_DATA_DIR / f"newpath{i + 1}.path"))

        parking_start = vars_[i + _NUM_ROBOTS]
        assert isinstance(parking_start, TrajectoryEnvelope)
        parking_start.component = f"Robot{i}"
        parking_start.symbolic_variable_activity.set_symbolic_domain("Parking (initial)")
        parking_start.robot_id = i
        parking_start.set_footprint(_WIDTH, _LENGTH, 0.0, 0.0)
        parking_start.trajectory = Trajectory([driving.trajectory.pose[0]])
        parking_start.refinable = False

        parking_final = vars_[i + 2 * _NUM_ROBOTS]
        assert isinstance(parking_final, TrajectoryEnvelope)
        parking_final.component = f"Robot{i}"
        parking_final.symbolic_variable_activity.set_symbolic_domain("Parking (final)")
        parking_final.robot_id = i
        parking_final.set_footprint(_WIDTH, _LENGTH, 0.0, 0.0)
        parking_final.trajectory = Trajectory([driving.trajectory.pose[-1]])
        parking_final.refinable = False

        meets_parking_start_driving = AllenIntervalConstraint(AllenIntervalConstraint.Type.Meets)
        meets_parking_start_driving.from_ = parking_start
        meets_parking_start_driving.to = driving
        solver.add_constraints(meets_parking_start_driving)

        meets_driving_parking_final = AllenIntervalConstraint(AllenIntervalConstraint.Type.Meets)
        meets_driving_parking_final.from_ = driving
        meets_driving_parking_final.to = parking_final
        solver.add_constraints(meets_driving_parking_final)

        release = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Release, Bounds(solver.origin, solver.origin)
        )
        release.from_ = parking_start
        release.to = parking_start
        solver.add_constraint(release)

        parking_dur_start = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Release, Bounds(_PARKING_DURATION, APSPSolver.INF)
        )
        parking_dur_start.from_ = parking_start
        parking_dur_start.to = parking_start
        solver.add_constraint(parking_dur_start)

        parking_final_forever = AllenIntervalConstraint(AllenIntervalConstraint.Type.Forever)
        parking_final_forever.from_ = parking_final
        parking_final_forever.to = parking_final
        solver.add_constraint(parking_final_forever)

    # Create a meta-constraint of type Map
    #  -- meta-variables are TrajectoryEnvelopes that overlap in time and space
    #  -- meta-values are BeforeOrMeets constraints that separate in time
    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    # Refinement of trajectory envelopes allows separating overlapping envelopes in time.
    meta_solver.refine_trajectory_envelopes()

    # Call the scheduler (backtracking search over assignments of meta-values to
    # meta-variables) -- in this case, resolving BeforeOrMeets constraints.
    solved = meta_solver.backtrack()
    print("Solved?", solved)
    if solved:
        print("Added resolvers:")
        print(meta_solver.get_added_resolvers())

    ans_list = solver.get_constraint_solvers_from_constraint_solver_hierarchy(ActivityNetworkSolver)
    ans = ans_list[0]
    animator = ConstraintNetworkAnimator(ans, 1000)

    for i in range(_NUM_ROBOTS):
        component = f"Robot{i}"
        animator.add_dispatching_functions(_RobotDispatchingFunction(component, animator))

    try:
        time.sleep(_RUN_SECONDS)
    finally:
        animator.teardown()


if __name__ == "__main__":
    main()
