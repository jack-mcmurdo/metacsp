"""Port of examples/meta/TestCausalPlanning.java.

The Java original also drives a live Swing timeline (``TimelinePublisher``/
``TimelineVisualizer``) and constraint-network viewer
(``ConstraintNetwork.draw``); replaced here by a bounded
``metacsp.viz.timeline.TimelineWindow`` refresh (M21) rather than an
indefinitely-open Swing window.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from metacsp.meta.simple_planner import SimpleDomain
from metacsp.meta.simple_planner.simple_planner import SimplePlanner
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.viz.app import VizApp
from metacsp.viz.timeline import TimelineWindow

DOMAIN_FILE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "data"
    / "domains"
    / "testCausalPlanningDomain.ddl"
)


def main() -> None:
    planner = SimplePlanner(0, 6000, 0)
    SimpleDomain.parse_domain(planner, str(DOMAIN_FILE), SimpleDomain)

    ground_solver = cast(ActivityNetworkSolver, planner.constraint_solvers[0])

    # INITIAL AND GOAL STATE DEFS
    one = cast(SymbolicVariableActivity, ground_solver.create_variable("Robot"))
    one.set_symbolic_domain("At(?to)")
    # ... this is a goal (i.e., an activity to justify through the meta-constraint).
    one.marking = SimpleDomain.markings.UNJUSTIFIED
    # ... let's also give it a minimum duration.
    duration_one = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Duration, Bounds(7, APSPSolver.INF)
    )
    duration_one.from_ = one
    duration_one.to = one
    ground_solver.add_constraints(duration_one)

    # Initial condition.
    init1 = cast(SymbolicVariableActivity, ground_solver.create_variable("Robot"))
    init1.set_symbolic_domain("At(?from)")
    init1.marking = SimpleDomain.markings.JUSTIFIED
    duration_init1 = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Duration, Bounds(1300, APSPSolver.INF)
    )
    duration_init1.from_ = init1
    duration_init1.to = init1
    ground_solver.add_constraints(duration_init1)

    print("Solved?", planner.backtrack())

    app = VizApp(title="TestCausalPlanning")
    window = TimelineWindow(
        ground_solver.constraint_network,
        ["Robot", "LocalizationService", "RFIDReader", "LaserScanner"],
    )
    app.create()
    window.build(app)
    try:
        window.refresh()
    finally:
        window.destroy()
        app.destroy()


if __name__ == "__main__":
    main()
