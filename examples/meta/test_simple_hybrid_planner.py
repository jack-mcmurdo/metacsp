"""Port of examples/meta/TestSimpleHybridPlanner.java.

The Java original also draws constraint networks (``ConstraintNetwork.draw``)
and drives a live Swing timeline (``TimelinePublisher``/``TimelineVisualizer``);
none of that Swing/viz machinery is ported yet (see D10, M21) -- this example
just parses the domain, solves once, and prints the result plus a
start-time-sorted dump of the resulting activities (mirroring the Java
source's own debug printout).

The Java source has three alternative ``FluentBasedSimpleDomain.parseDomain``
calls (two commented out); the uncommented one -- ``testFieldOfViewDomain.ddl``
-- is the one ported here, matching the pinned Java commit exactly.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from metacsp.framework.constraint import Constraint
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
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint_solver import (
    RectangleConstraintSolver,
)
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

DOMAIN_FILE = (
    Path(__file__).resolve().parents[2] / "tests" / "data" / "domains" / "testFieldOfViewDomain.ddl"
)

PAD = 0
DURATION = 1000


class OntologicalSpatialProperty:
    """A plain local stand-in for the skipped, dead-code
    ``multi/spatial/rectangleAlgebraNew/toRemove/OntologicalSpatialProperty.java``
    (see PLAN.md's skip list and M11's identical precedent) -- just the three
    booleans this example reads/writes via
    :attr:`~metacsp.spatial.utility.spatial_assertional_relation.SpatialAssertionalRelation.ontological_prop`
    (typed ``Any``)."""

    def __init__(
        self, is_graspable: bool = True, is_movable: bool = True, is_obstacle: bool = False
    ) -> None:
        self.is_graspable = is_graspable
        self.is_movable = is_movable
        self.is_obstacle = is_obstacle


def _set_fluent_into_network(
    cons: list[Constraint],
    ground_spatial_fluent_solver: SpatialFluentSolver,
    component: str,
    name: str,
    symbolic_domain: str,
    mk: SimpleDomain.markings,
    release: int,
) -> None:
    sf = ground_spatial_fluent_solver.create_variable(component)
    sf.name = name
    sf.rectangular_region.name = name
    sf.activity.set_symbolic_domain(symbolic_domain)
    sf.activity.marking = mk

    if mk is markings.JUSTIFIED:
        on_duration = AllenIntervalConstraint(Type.Duration, Bounds(DURATION, APSPSolver.INF))
        on_duration.from_ = sf.activity
        on_duration.to = sf.activity
        cons.append(on_duration)

        release_on = AllenIntervalConstraint(Type.Release, Bounds(release, release))
        release_on.from_ = sf.activity
        release_on.to = sf.activity
        cons.append(release_on)


def _insert_current_state_current_goal(ground_spatial_fluent_solver: SpatialFluentSolver) -> None:
    cons: list[Constraint] = []

    _set_fluent_into_network(
        cons,
        ground_spatial_fluent_solver,
        "atLocation",
        "table1",
        "at_robot1_table1()",
        markings.JUSTIFIED,
        1,
    )
    _set_fluent_into_network(
        cons,
        ground_spatial_fluent_solver,
        "atLocation",
        "fork1",
        "at_fork1_table1()",
        markings.JUSTIFIED,
        8,
    )
    _set_fluent_into_network(
        cons,
        ground_spatial_fluent_solver,
        "atLocation",
        "knife1",
        "at_knife1_table1()",
        markings.JUSTIFIED,
        8,
    )
    _set_fluent_into_network(
        cons,
        ground_spatial_fluent_solver,
        "atLocation",
        "cup1",
        "at_cup1_table1()",
        markings.UNJUSTIFIED,
        -1,
    )

    # ------------------------------------------------------------------
    # Initial state.
    # ------------------------------------------------------------------
    two = cast(
        SymbolicVariableActivity,
        ground_spatial_fluent_solver.constraint_solvers[1].create_variable("RobotProprioception"),
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

    ground_spatial_fluent_solver.constraint_solvers[1].add_constraints(*cons)


def _add_on_table_constraint(srules: list[SpatialRule], name: str) -> None:
    within_reach_y_lower = Bounds(5, 20)
    within_reach_y_upper = Bounds(5, APSPSolver.INF)
    within_reach_x_lower = Bounds(5, APSPSolver.INF)
    within_reach_x_upper = Bounds(5, APSPSolver.INF)

    srules.append(
        SpatialRule(
            name,
            "table",
            binary_ra_constraint=RectangleConstraint(
                AllenIntervalConstraint(Type.During, within_reach_x_lower, within_reach_x_upper),
                AllenIntervalConstraint(Type.During, within_reach_y_lower, within_reach_y_upper),
            ),
        )
    )


def _get_spatial_knowledge(srules: list[SpatialRule]) -> None:
    knife_size_x = Bounds(4, 8)
    knife_size_y = Bounds(18, 24)
    cup_size_x = Bounds(4, 7)
    cup_size_y = Bounds(4, 7)
    fork_size_x = Bounds(4, 8)
    fork_size_y = Bounds(18, 24)

    srules.append(
        SpatialRule(
            "knife",
            "knife",
            unary_ra_constraint=UnaryRectangleConstraint(
                UnaryRectangleConstraint.Type.Size, knife_size_x, knife_size_y
            ),
        )
    )
    srules.append(
        SpatialRule(
            "cup",
            "cup",
            unary_ra_constraint=UnaryRectangleConstraint(
                UnaryRectangleConstraint.Type.Size, cup_size_x, cup_size_y
            ),
        )
    )
    srules.append(
        SpatialRule(
            "fork",
            "fork",
            unary_ra_constraint=UnaryRectangleConstraint(
                UnaryRectangleConstraint.Type.Size, fork_size_x, fork_size_y
            ),
        )
    )

    # Everything should be on the table.
    _add_on_table_constraint(srules, "fork")
    _add_on_table_constraint(srules, "knife")
    _add_on_table_constraint(srules, "cup")

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


def _insert_at_constraint(
    sa_relations: list[SpatialAssertionalRelation],
    name: str,
    xl: int,
    xu: int,
    yl: int,
    yu: int,
    movable: bool,
) -> None:
    table_assertion = SpatialAssertionalRelation(name + "1", name)
    if xl == 0 and xu == 0 and yl == 0 and yu == 0:
        table_assertion.unary_at_rectangle_constraint = UnaryRectangleConstraint(
            UnaryRectangleConstraint.Type.At,
            Bounds(0, APSPSolver.INF),
            Bounds(0, APSPSolver.INF),
            Bounds(0, APSPSolver.INF),
            Bounds(0, APSPSolver.INF),
        )
    else:
        table_assertion.unary_at_rectangle_constraint = UnaryRectangleConstraint(
            UnaryRectangleConstraint.Type.At,
            Bounds(xl, xl),
            Bounds(xu, xu),
            Bounds(yl, yl),
            Bounds(yu, yu),
        )
    table_onto = OntologicalSpatialProperty()
    table_onto.is_movable = movable
    table_assertion.ontological_prop = table_onto
    sa_relations.append(table_assertion)


def _get_assertional_rule(sa_relations: list[SpatialAssertionalRelation]) -> None:
    # Both fork and knife should be replaced.
    _insert_at_constraint(sa_relations, "table", 0, 60, 0, 99, False)
    _insert_at_constraint(sa_relations, "fork", 20, 26, 13, 32, True)
    _insert_at_constraint(sa_relations, "knife", 30, 36, 10, 33, True)
    _insert_at_constraint(sa_relations, "cup", 0, 0, 0, 0, True)


def main() -> None:
    simple_hybrid_planner = SimpleHybridPlanner(0, 100000, 0)

    FluentBasedSimpleDomain.parse_domain(
        simple_hybrid_planner, str(DOMAIN_FILE), FluentBasedSimpleDomain
    )

    # Most critical conflict is the one with most activities: no explicit
    # var/value ordering heuristics are set (Java passes ``null, null`` too).
    meta_spatial_adherence = MetaSpatialAdherenceConstraint(None, None)
    ground_solver = cast(SpatialFluentSolver, simple_hybrid_planner.constraint_solvers[0])

    # ------------------------------------------------------------------
    meta_occupied_constraint = MetaOccupiedTimesBasedConstraint(None, None)
    meta_occupied_constraint.set_pad(PAD)
    # ------------------------------------------------------------------
    # General and assertional spatial knowledge.
    srules: list[SpatialRule] = []
    sa_relations: list[SpatialAssertionalRelation] = []

    _get_spatial_knowledge(srules)
    _get_assertional_rule(sa_relations)
    _insert_current_state_current_goal(ground_solver)
    # ------------------------------------------------------------------
    meta_spatial_adherence.set_spatial_rules(*srules)
    meta_spatial_adherence.set_spatial_assertional_relations(sa_relations)
    meta_spatial_adherence.set_initial_goal(["cup1"])

    simple_hybrid_planner.add_meta_constraint(meta_occupied_constraint)
    simple_hybrid_planner.add_meta_constraint(meta_spatial_adherence)

    solved = simple_hybrid_planner.backtrack()
    print("Solved?", solved)

    # ------------------------------------------------------------------
    recs: dict[str, object] = {}
    rectangle_solver = cast(RectangleConstraintSolver, ground_solver.constraint_solvers[0])
    for name, bb in rectangle_solver.extract_all_bounding_boxes_from_stps().items():
        if name.endswith("1"):
            rect = bb.get_almost_centre_rectangle()
            print(name, "-->", rect)
            recs[name] = rect

    act_solver = cast(ActivityNetworkSolver, ground_solver.constraint_solvers[1])
    # ------------------------------------------------------------------
    # Sort activities by start time for debugging purposes.
    start_times: dict[SymbolicVariableActivity, int] = {}
    for var in act_solver.get_variables():
        act = cast(SymbolicVariableActivity, var)
        start_times[act] = act.temporal_variable.start.lower_bound

    for act, start in sorted(start_times.items(), key=lambda kv: kv[1]):
        print(act, "-->", start)


if __name__ == "__main__":
    main()
