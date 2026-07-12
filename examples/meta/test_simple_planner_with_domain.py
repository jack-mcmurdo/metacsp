"""Port of examples/meta/TestSimplePlannerWithDomain.java.

The Java original also drives a live Swing timeline (``TimelinePublisher``/
``TimelineVisualizer``) and constraint-network viewer (``ConstraintNetwork
.draw``, ``planner.draw()``); none of that Swing/viz machinery is ported yet
(see D10, M21) -- this example just parses the domain, solves once, and
prints the result.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from metacsp.meta.simple_planner import SimpleDomain, SimplePlanner
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

Type = AllenIntervalConstraint.Type

DOMAIN_FILE = (
    Path(__file__).resolve().parents[2] / "tests" / "data" / "domains" / "testSimplePlanner.ddl"
)


def main() -> None:
    # Create planner.
    planner = SimplePlanner(0, 600, 0)

    SimpleDomain.parse_domain(planner, str(DOMAIN_FILE), SimpleDomain)

    # This is a pointer toward the ground constraint network of the planner.
    ground_solver = cast(ActivityNetworkSolver, planner.constraint_solvers[0])

    # INITIAL AND GOAL STATE DEFS
    one = cast(SymbolicVariableActivity, ground_solver.create_variable("Robot1"))
    one.set_symbolic_domain("MoveTo()")
    # ... this is a goal (i.e., an activity to justify through the meta-constraint).
    one.marking = SimpleDomain.markings.UNJUSTIFIED
    # ... let's also give it a minimum duration.
    duration_one = AllenIntervalConstraint(Type.Duration, Bounds(7, APSPSolver.INF))
    duration_one.from_ = one
    duration_one.to = one

    two = cast(SymbolicVariableActivity, ground_solver.create_variable("Robot2"))
    two.set_symbolic_domain("MoveTo()")
    two.marking = SimpleDomain.markings.UNJUSTIFIED
    duration_two = AllenIntervalConstraint(Type.Duration, Bounds(7, APSPSolver.INF))
    duration_two.from_ = two
    duration_two.to = two

    ground_solver.add_constraints(duration_one, duration_two)

    # We can also specify that goals should be related in time somehow...
    # after = AllenIntervalConstraint(Type.After, *Type.After.get_default_bounds())
    # after.from_ = one
    # after.to = two
    # ground_solver.add_constraint(after)

    solved = planner.backtrack()
    print("SOLVED?", solved)
    print("one:", one)
    print("two:", two)


if __name__ == "__main__":
    main()
