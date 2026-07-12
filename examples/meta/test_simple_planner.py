"""Port of examples/meta/TestSimplePlanner.java.

The Java original also drives a live Swing timeline (``TimelinePublisher``/
``TimelineVisualizer``) and constraint-network viewer (``ConstraintNetwork
.draw``, ``planner.draw()``); none of that Swing/viz machinery is ported yet
(see D10, M21) -- this example just builds the domain, solves once, and
prints the result.
"""

from __future__ import annotations

from typing import cast

from metacsp.meta.simple_planner import SimpleDomain, SimpleOperator, SimplePlanner
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

Type = AllenIntervalConstraint.Type


def main() -> None:
    planner = SimplePlanner(0, 600, 0)
    # This is a pointer toward the ActivityNetworkSolver of the planner.
    ground_solver = cast(ActivityNetworkSolver, planner.constraint_solvers[0])

    rd = SimpleDomain([6, 6, 6], ["power", "usbport", "serialport"], "TestDomain")

    # State which components are actuators (i.e. actions).
    rd.add_actuator("Robot1")
    rd.add_actuator("Robot2")
    rd.add_actuator("LocalizationService")
    rd.add_actuator("RFIDReader1")
    rd.add_actuator("LaserScanner1")

    # Here we create two AllenIntervalConstraints for use in the operators
    # defined below.
    duration_move_to = AllenIntervalConstraint(Type.Duration, Bounds(5, APSPSolver.INF))
    move_to_during_localization = AllenIntervalConstraint(
        Type.During, *Type.During.get_default_bounds()
    )

    # New operator: the first parameter is the name, the second are the
    # constraints, the third are requirement activities, fourth means no
    # usage of resources.
    operator1 = SimpleOperator(
        "Robot1::MoveTo()",
        [move_to_during_localization],
        ["LocalizationService::Localization()"],
        None,
    )
    # We can add constraints to the operator even after it has been created:
    # this is useful for adding unary constraints on the head (which has
    # index 0).
    operator1.add_constraint(duration_move_to, 0, 0)
    rd.add_operator(operator1)

    # We give robot 2 the same capability...
    operator1a = SimpleOperator(
        "Robot2::MoveTo()",
        [move_to_during_localization],
        ["LocalizationService::Localization()"],
        None,
    )
    operator1a.add_constraint(duration_move_to, 0, 0)
    rd.add_operator(operator1a)

    # This operator states that LocalizationService::Localization needs
    # RFIDReader1::On() and doesn't consume resources.
    localization_during_rfid = AllenIntervalConstraint(
        Type.During, *Type.During.get_default_bounds()
    )
    operator2 = SimpleOperator(
        "LocalizationService::Localization()",
        [localization_during_rfid],
        ["RFIDReader1::On()"],
        None,
    )
    rd.add_operator(operator2)

    # This operator has the same name as the previous one, but different
    # requirements.
    localization_during_laser = AllenIntervalConstraint(
        Type.During, *Type.During.get_default_bounds()
    )
    operator3 = SimpleOperator(
        "LocalizationService::Localization()",
        [localization_during_laser],
        ["LaserScanner1::On()"],
        None,
    )
    rd.add_operator(operator3)

    # This operator has no requirement but consumes 5 units of the first
    # resource and 7 of the second.
    operator4 = SimpleOperator("RFIDReader1::On()", None, None, [5, 7])
    rd.add_operator(operator4)

    # Similar to the previous operator.
    operator5 = SimpleOperator("LaserScanner1::On()", None, None, [5, 1])
    rd.add_operator(operator5)

    # This adds the domain as a meta-constraint of the SimplePlanner...
    planner.add_meta_constraint(rd)
    # ... and we also add all its resources as separate meta-constraints.
    for sch in rd.get_scheduling_meta_constraints():
        planner.add_meta_constraint(sch)

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
    # after.from_ = two
    # after.to = one
    # ground_solver.add_constraint(after)

    solved = planner.backtrack()
    print("SOLVED?", solved)
    print("one:", one)
    print("two:", two)


if __name__ == "__main__":
    main()
