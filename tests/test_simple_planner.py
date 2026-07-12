"""Tests for meta/simplePlanner (M16).

There is no ported JUnit test class for SimplePlanner in the Java source
(``tests/meta/`` has no ``TestSimplePlanner*.java``); PLAN.md's explicit
acceptance criterion for M16 is "assert a plan is found on one ported
domain", which these tests do -- both the hand-built domain from
``TestSimplePlanner.java`` and the ``.ddl``-parsed domain from
``TestSimplePlannerWithDomain.java``. Assertions beyond "a plan is found"
check plan *validity* (both goals justified, activities scheduled
consistently), not an exact search trace, per PLAN.md's "search-order
divergence" risk note.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from metacsp.meta.simple_planner import SimpleDomain, SimpleOperator, SimplePlanner
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

Type = AllenIntervalConstraint.Type

DOMAIN_FILE = Path(__file__).resolve().parent / "data" / "domains" / "testSimplePlanner.ddl"


def _build_hand_domain(planner: SimplePlanner) -> SimpleDomain:
    """Mirrors TestSimplePlanner.java's hand-built domain."""
    rd = SimpleDomain([6, 6, 6], ["power", "usbport", "serialport"], "TestDomain")

    rd.add_actuator("Robot1")
    rd.add_actuator("Robot2")
    rd.add_actuator("LocalizationService")
    rd.add_actuator("RFIDReader1")
    rd.add_actuator("LaserScanner1")

    duration_move_to = AllenIntervalConstraint(Type.Duration, Bounds(5, APSPSolver.INF))
    move_to_during_localization = AllenIntervalConstraint(
        Type.During, *Type.During.get_default_bounds()
    )

    operator1 = SimpleOperator(
        "Robot1::MoveTo()",
        [move_to_during_localization],
        ["LocalizationService::Localization()"],
        None,
    )
    operator1.add_constraint(duration_move_to, 0, 0)
    rd.add_operator(operator1)

    operator1a = SimpleOperator(
        "Robot2::MoveTo()",
        [move_to_during_localization],
        ["LocalizationService::Localization()"],
        None,
    )
    operator1a.add_constraint(duration_move_to, 0, 0)
    rd.add_operator(operator1a)

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

    operator4 = SimpleOperator("RFIDReader1::On()", None, None, [5, 7])
    rd.add_operator(operator4)

    operator5 = SimpleOperator("LaserScanner1::On()", None, None, [5, 1])
    rd.add_operator(operator5)

    planner.add_meta_constraint(rd)
    for sch in rd.get_scheduling_meta_constraints():
        planner.add_meta_constraint(sch)

    return rd


def _add_goals(
    planner: SimplePlanner,
) -> tuple[SymbolicVariableActivity, SymbolicVariableActivity]:
    ground_solver = cast(ActivityNetworkSolver, planner.constraint_solvers[0])

    one = cast(SymbolicVariableActivity, ground_solver.create_variable("Robot1"))
    one.set_symbolic_domain("MoveTo()")
    one.marking = SimpleDomain.markings.UNJUSTIFIED
    duration_one = AllenIntervalConstraint(Type.Duration, Bounds(7, APSPSolver.INF))
    duration_one.from_ = one
    duration_one.to = one

    two = cast(SymbolicVariableActivity, ground_solver.create_variable("Robot2"))
    two.set_symbolic_domain("MoveTo()")
    two.marking = SimpleDomain.markings.UNJUSTIFIED
    duration_two = AllenIntervalConstraint(Type.Duration, Bounds(7, APSPSolver.INF))
    duration_two.from_ = two
    duration_two.to = two

    assert ground_solver.add_constraints(duration_one, duration_two)
    return one, two


class TestSimplePlanner:
    def test_hand_built_domain_finds_plan(self) -> None:
        planner = SimplePlanner(0, 600, 0)
        _build_hand_domain(planner)
        one, two = _add_goals(planner)

        # Before planning, both goals are still unjustified.
        assert one.marking == SimpleDomain.markings.UNJUSTIFIED
        assert two.marking == SimpleDomain.markings.UNJUSTIFIED

        assert planner.backtrack()

        # A valid plan justifies every originally-unjustified goal.
        assert one.marking == SimpleDomain.markings.JUSTIFIED
        assert two.marking == SimpleDomain.markings.JUSTIFIED

        # The ground network must remain temporally consistent (activities
        # got real, non-empty [est,eet] bounds).
        ground_solver = cast(ActivityNetworkSolver, planner.constraint_solvers[0])
        for act in cast("list[SymbolicVariableActivity]", ground_solver.get_variables()):
            assert act.temporal_variable.est <= act.temporal_variable.eet

    def test_ddl_domain_finds_plan(self) -> None:
        assert DOMAIN_FILE.is_file()
        planner = SimplePlanner(0, 600, 0)
        dom = SimpleDomain.parse_domain(planner, str(DOMAIN_FILE), SimpleDomain)
        assert dom is not None

        one, two = _add_goals(planner)

        assert planner.backtrack()

        assert one.marking == SimpleDomain.markings.JUSTIFIED
        assert two.marking == SimpleDomain.markings.JUSTIFIED

    def test_no_goals_trivially_solved(self) -> None:
        """With no UNJUSTIFIED activities there is nothing to plan for --
        backtrack() must succeed immediately (mirrors
        MetaConstraintSolver.backtrack()'s "no conflicts found" path)."""
        planner = SimplePlanner(0, 600, 0)
        _build_hand_domain(planner)
        assert planner.backtrack()
