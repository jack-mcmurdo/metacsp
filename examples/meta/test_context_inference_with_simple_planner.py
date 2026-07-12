"""Port of examples/meta/TestContextInferenceWithSimplePlanner.java.

The Java original also draws the constraint network
(``ConstraintNetwork.draw``, ``planner.draw()`` -- Swing, not ported, see
D10) and publishes a one-shot timeline image; replaced here by one
``metacsp.viz.timeline.TimelineWindow`` refresh (M21).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from metacsp.framework.constraint import Constraint
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
    Path(__file__).resolve().parents[2] / "tests" / "data" / "domains" / "testProactivePlanning.ddl"
)


def main() -> None:
    planner = SimplePlanner(0, 600, 0)
    SimpleDomain.parse_domain(planner, str(DOMAIN_FILE), SimpleDomain)

    ground_solver = cast(ActivityNetworkSolver, planner.constraint_solvers[0])

    # GOAL: infer cooking.
    one = cast(SymbolicVariableActivity, ground_solver.create_variable("Human"))
    one.set_symbolic_domain("Cooking()")
    # ... this is a goal (i.e., an activity to justify through the meta-constraint).
    one.marking = SimpleDomain.markings.UNJUSTIFIED

    # SENSORS: user in kitchen from 1 until at least 20.
    s1 = cast(SymbolicVariableActivity, ground_solver.create_variable("Location"))
    s1.set_symbolic_domain("Kitchen()")
    # ... this is a sensor value (i.e., an activity that is already justified).
    s1.marking = SimpleDomain.markings.JUSTIFIED
    # ... let's also give it a minimum duration.
    duration_s1 = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Duration, Bounds(20, APSPSolver.INF)
    )
    duration_s1.from_ = s1
    duration_s1.to = s1
    # Let's release it.
    rel_s1 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(1, 1))
    rel_s1.from_ = s1
    rel_s1.to = s1

    # SENSORS: stove is on from 4 and lasts 10.
    s2 = cast(SymbolicVariableActivity, ground_solver.create_variable("Stove"))
    s2.set_symbolic_domain("On()")
    # ... this is a sensor value (i.e., an activity that is already justified).
    s2.marking = SimpleDomain.markings.JUSTIFIED
    # ... let's also give it a minimum duration.
    duration_s2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Duration, Bounds(10, 10))
    duration_s2.from_ = s2
    duration_s2.to = s2
    # Let's release it.
    rel_s2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(4, 4))
    rel_s2.from_ = s2
    rel_s2.to = s2

    cons: list[Constraint] = [duration_s1, duration_s2, rel_s1, rel_s2]
    ground_solver.add_constraints(*cons)

    print("Solved?", planner.backtrack())

    app = VizApp(title="TestContextInferenceWithSimplePlanner")
    window = TimelineWindow(
        ground_solver.constraint_network,
        [
            "Human",
            "Location",
            "Stove",
            "Robot",
            "LocalizationService",
            "LaserScanner",
            "RFIDReader",
        ],
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
