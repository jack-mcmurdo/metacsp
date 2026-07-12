"""Tests for meta/hybridPlanner (M18).

There is no ported JUnit test class for the hybrid planner in the Java
source (``tests/`` has no ``TestSimpleHybridPlanner*.java``); PLAN.md's
explicit acceptance criterion for M18 is a pytest "from one example's
outcome" -- this mirrors ``examples/meta/test_simple_hybrid_planner.py``
(itself a port of ``TestSimpleHybridPlanner.java``, the "well-set table"
scenario: cup1 needs a spot on the table currently occupied by fork1/knife1,
which the hybrid planner must first move aside) and asserts the outcome the
Java source's own ``System.out.println("Solved?", ...)``-equivalent would
show: ``backtrack()`` succeeds and every activity ends up JUSTIFIED with a
symbolic domain consistent with the original goal, per PLAN.md's
"search-order divergence" risk note (assert solution validity, not an exact
search trace).

This scenario takes on the order of a minute of pure-Python meta-CSP search
(PLAN.md's Edge cases & risks section notes this is expected and acceptable).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from metacsp.meta.hybrid_planner import (
    FluentBasedSimpleDomain,
    MetaOccupiedTimesBasedConstraint,
    MetaSpatialAdherenceConstraint,
    SimpleHybridPlanner,
)
from metacsp.meta.simple_planner import SimpleDomain
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver import SpatialFluentSolver
from metacsp.spatial.utility.spatial_assertional_relation import SpatialAssertionalRelation
from metacsp.spatial.utility.spatial_rule import SpatialRule
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

Type = AllenIntervalConstraint.Type
markings = SimpleDomain.markings

DOMAIN_FILE = Path(__file__).resolve().parent / "data" / "domains" / "testFieldOfViewDomain.ddl"


class _Onto:
    """Plain placeholder for the skipped, dead-code
    ``OntologicalSpatialProperty.java`` (see M11/M18 precedent)."""

    def __init__(self, is_movable: bool = True) -> None:
        self.is_graspable = True
        self.is_movable = is_movable
        self.is_obstacle = False


def _set_fluent(
    cons: list,
    solver: SpatialFluentSolver,
    component: str,
    name: str,
    symbol: str,
    mk: SimpleDomain.markings,
    release: int,
) -> None:
    sf = solver.create_variable(component)
    sf.name = name
    sf.rectangular_region.name = name
    sf.activity.set_symbolic_domain(symbol)
    sf.activity.marking = mk
    if mk is markings.JUSTIFIED:
        on_duration = AllenIntervalConstraint(Type.Duration, Bounds(1000, APSPSolver.INF))
        on_duration.from_ = sf.activity
        on_duration.to = sf.activity
        cons.append(on_duration)
        release_on = AllenIntervalConstraint(Type.Release, Bounds(release, release))
        release_on.from_ = sf.activity
        release_on.to = sf.activity
        cons.append(release_on)


def _insert_current_state_current_goal(ground_solver: SpatialFluentSolver) -> None:
    cons: list = []
    _set_fluent(
        cons, ground_solver, "atLocation", "table1", "at_robot1_table1()", markings.JUSTIFIED, 1
    )
    _set_fluent(
        cons, ground_solver, "atLocation", "fork1", "at_fork1_table1()", markings.JUSTIFIED, 8
    )
    _set_fluent(
        cons, ground_solver, "atLocation", "knife1", "at_knife1_table1()", markings.JUSTIFIED, 8
    )
    _set_fluent(
        cons, ground_solver, "atLocation", "cup1", "at_cup1_table1()", markings.UNJUSTIFIED, -1
    )

    two = cast(
        SymbolicVariableActivity,
        ground_solver.constraint_solvers[1].create_variable("RobotProprioception"),
    )
    two.set_symbolic_domain("holding_cup1()")
    two.marking = markings.JUSTIFIED
    release_holding = AllenIntervalConstraint(Type.Release, Bounds(1, 1))
    release_holding.from_ = two
    release_holding.to = two
    cons.append(release_holding)
    duration_holding = AllenIntervalConstraint(Type.Duration, Bounds(10, APSPSolver.INF))
    duration_holding.from_ = two
    duration_holding.to = two
    cons.append(duration_holding)

    ground_solver.constraint_solvers[1].add_constraints(*cons)


def _spatial_knowledge() -> list[SpatialRule]:
    srules: list[SpatialRule] = []
    srules.append(
        SpatialRule(
            "knife",
            "knife",
            unary_ra_constraint=UnaryRectangleConstraint(
                UnaryRectangleConstraint.Type.Size, Bounds(4, 8), Bounds(18, 24)
            ),
        )
    )
    srules.append(
        SpatialRule(
            "cup",
            "cup",
            unary_ra_constraint=UnaryRectangleConstraint(
                UnaryRectangleConstraint.Type.Size, Bounds(4, 7), Bounds(4, 7)
            ),
        )
    )
    srules.append(
        SpatialRule(
            "fork",
            "fork",
            unary_ra_constraint=UnaryRectangleConstraint(
                UnaryRectangleConstraint.Type.Size, Bounds(4, 8), Bounds(18, 24)
            ),
        )
    )

    def on_table(name: str) -> SpatialRule:
        return SpatialRule(
            name,
            "table",
            binary_ra_constraint=RectangleConstraint(
                AllenIntervalConstraint(
                    Type.During, Bounds(5, APSPSolver.INF), Bounds(5, APSPSolver.INF)
                ),
                AllenIntervalConstraint(Type.During, Bounds(5, 20), Bounds(5, APSPSolver.INF)),
            ),
        )

    srules.append(on_table("fork"))
    srules.append(on_table("knife"))
    srules.append(on_table("cup"))

    srules.append(
        SpatialRule(
            "cup",
            "knife",
            binary_ra_constraint=RectangleConstraint(
                AllenIntervalConstraint(Type.Before, Bounds(15, 20)),
                AllenIntervalConstraint(Type.During, *Type.During.get_default_bounds()),
            ),
        )
    )
    srules.append(
        SpatialRule(
            "cup",
            "fork",
            binary_ra_constraint=RectangleConstraint(
                AllenIntervalConstraint(Type.After, Bounds(15, 20)),
                AllenIntervalConstraint(Type.During, *Type.During.get_default_bounds()),
            ),
        )
    )
    return srules


def _insert_at(
    sa_relations: list[SpatialAssertionalRelation],
    name: str,
    xl: int,
    xu: int,
    yl: int,
    yu: int,
    movable: bool,
) -> None:
    rel = SpatialAssertionalRelation(name + "1", name)
    if xl == 0 and xu == 0 and yl == 0 and yu == 0:
        rel.unary_at_rectangle_constraint = UnaryRectangleConstraint(
            UnaryRectangleConstraint.Type.At,
            Bounds(0, APSPSolver.INF),
            Bounds(0, APSPSolver.INF),
            Bounds(0, APSPSolver.INF),
            Bounds(0, APSPSolver.INF),
        )
    else:
        rel.unary_at_rectangle_constraint = UnaryRectangleConstraint(
            UnaryRectangleConstraint.Type.At,
            Bounds(xl, xl),
            Bounds(xu, xu),
            Bounds(yl, yl),
            Bounds(yu, yu),
        )
    rel.ontological_prop = _Onto(is_movable=movable)
    sa_relations.append(rel)


def _assertional_rule() -> list[SpatialAssertionalRelation]:
    sa_relations: list[SpatialAssertionalRelation] = []
    _insert_at(sa_relations, "table", 0, 60, 0, 99, False)
    _insert_at(sa_relations, "fork", 20, 26, 13, 32, True)
    _insert_at(sa_relations, "knife", 30, 36, 10, 33, True)
    _insert_at(sa_relations, "cup", 0, 0, 0, 0, True)
    return sa_relations


def test_hybrid_planner_solves_well_set_table() -> None:
    planner = SimpleHybridPlanner(0, 100000, 0)
    dom = FluentBasedSimpleDomain.parse_domain(planner, str(DOMAIN_FILE), FluentBasedSimpleDomain)
    assert dom is not None

    ground_solver = cast(SpatialFluentSolver, planner.constraint_solvers[0])

    meta_occupied = MetaOccupiedTimesBasedConstraint(None, None)
    meta_occupied.set_pad(0)

    meta_spatial_adherence = MetaSpatialAdherenceConstraint(None, None)
    meta_spatial_adherence.set_spatial_rules(*_spatial_knowledge())
    meta_spatial_adherence.set_spatial_assertional_relations(_assertional_rule())
    meta_spatial_adherence.set_initial_goal(["cup1"])

    _insert_current_state_current_goal(ground_solver)

    planner.add_meta_constraint(meta_occupied)
    planner.add_meta_constraint(meta_spatial_adherence)

    solved = planner.backtrack()
    assert solved is True

    # Plan validity (per PLAN.md's search-order-divergence note): every
    # activity ends up justified, and cup1's original goal symbol survives
    # somewhere in the final, consistent activity network.
    act_solver = cast(ActivityNetworkSolver, ground_solver.constraint_solvers[1])
    activities = [cast(SymbolicVariableActivity, v) for v in act_solver.get_variables()]
    assert activities
    assert all(act.marking is markings.JUSTIFIED for act in activities)

    cup1_acts = [
        act
        for act in activities
        if act.component == "atLocation" and "at_cup1_table1" in act.symbolic_variable.symbols[0]
    ]
    assert cup1_acts, "the original cup1-on-table1 goal must be justified by some activity"
    # ``backtrack() is True`` already means the search terminated with no
    # outstanding conflict on any registered MetaConstraint (see
    # MetaConstraintSolver._backtrack_helper): re-scanning here would just
    # repeat the same (expensive) spatial-adherence/occupancy checks.
