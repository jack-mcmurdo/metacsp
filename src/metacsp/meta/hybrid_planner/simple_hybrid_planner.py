"""Port of meta/hybridPlanner/SimpleHybridPlanner.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.framework.variable_prototype import VariablePrototype
from metacsp.meta.hybrid_planner.fluent_based_simple_domain import FluentBasedSimpleDomain
from metacsp.meta.hybrid_planner.meta_occupied_constraint import MetaOccupiedConstraint
from metacsp.meta.hybrid_planner.meta_spatial_adherence_constraint import (
    MetaSpatialAdherenceConstraint,
)
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra.bounding_box import BoundingBox
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint_solver import (
    RectangleConstraintSolver,
)
from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent import SpatialFluent
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver import SpatialFluentSolver
from metacsp.spatial.reachability.reachability_constraint import ReachabilityConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.variable import Variable
    from metacsp.meta.simple_planner.simple_operator import SimpleOperator
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.spatial.utility.spatial_assertional_relation import SpatialAssertionalRelation

__all__ = ["SimpleHybridPlanner"]


class SimpleHybridPlanner(MetaConstraintSolver):
    """The M18 hybrid (causal + spatial) planner: a MetaConstraintSolver
    whose single ground solver is a
    :class:`~metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver.SpatialFluentSolver`,
    driven by a :class:`~.fluent_based_simple_domain.FluentBasedSimpleDomain`
    (causal/HTN reasoning), a :class:`~.meta_occupied_constraint.MetaOccupiedConstraint`
    (spatial occupancy conflicts) and a
    :class:`~.meta_spatial_adherence_constraint.MetaSpatialAdherenceConstraint`
    (spatial-knowledge adherence), all added as further MetaConstraints."""

    def __init__(self, origin: int, horizon: int, animation_time: int) -> None:
        super().__init__(
            [
                RectangleConstraint,
                UnaryRectangleConstraint,
                AllenIntervalConstraint,
                SymbolicValueConstraint,
                ReachabilityConstraint,
            ],
            animation_time,
            SpatialFluentSolver(origin, horizon),
        )
        self.horizon = horizon
        self.operators_along_branch: list[SimpleOperator] = []
        self.unification_along_branch: list[str] = []
        self._goals: list[SymbolicVariableActivity] = []  # original goals (not subgoals)
        self._var_involved_in_occupied_meta_constraints: list[SymbolicVariableActivity] = []
        self._learning_from_failure = False
        self._observation: dict[str, object] = {}
        self._conflict_ranking: dict[str, int] | None = None
        self._observed_spatial_fluents: list[SpatialFluent] = []
        self._manipulation_area_encoding = ""

    def pre_backtrack(self) -> None:
        pass

    def post_backtrack(self, mv: MetaVariable) -> None:
        if isinstance(mv.meta_constraint, FluentBasedSimpleDomain):
            assert mv.constraint_network is not None
            for v in mv.constraint_network.get_variables():
                v.marking = SimpleDomain.markings.UNJUSTIFIED

        arm_capacity = 100
        causal_reasoner: FluentBasedSimpleDomain | None = None
        for mc in self.meta_constraints:
            if isinstance(mc, FluentBasedSimpleDomain):
                causal_reasoner = mc
                for resource_name, rr in mc.get_resources().items():
                    if resource_name == "arm":
                        arm_capacity = rr.capacity

        if isinstance(mv.meta_constraint, MetaOccupiedConstraint):
            assert mv.constraint_network is not None
            for v in mv.constraint_network.get_variables():
                act = cast("SymbolicVariableActivity", v)
                if act not in self._var_involved_in_occupied_meta_constraints:
                    self._var_involved_in_occupied_meta_constraints.append(act)
            if arm_capacity <= len(self._var_involved_in_occupied_meta_constraints):
                assert causal_reasoner is not None
                causal_reasoner.apply_free_arm_heuristic(
                    self._var_involved_in_occupied_meta_constraints, "tray"
                )
                causal_reasoner.active_heuristic(False)
                self._learning_from_failure = True

    def learning_from_failure(self) -> bool:
        return self._learning_from_failure

    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        if meta_value.specialized_annotation is not None and _is_simple_operator(
            meta_value.specialized_annotation
        ):
            self.operators_along_branch.pop()

        ground_solver = cast(
            ActivityNetworkSolver,
            cast(SpatialFluentSolver, self.constraint_solvers[0]).constraint_solvers[1],
        )
        activity_to_remove: list[Variable] = []
        fluent_to_remove: list[Variable] = []
        rectangle_to_remove: list[Variable] = []

        for v in meta_value.get_variables():
            if not meta_variable.contains_variable(v):
                if isinstance(v, VariablePrototype):
                    if self._manipulation_area_encoding in cast(str, v.parameters[1]):
                        v_real = meta_value.get_substitution(v)
                        if v_real is not None:
                            fluent_to_remove.append(v_real)
                    else:
                        v_real = meta_value.get_substitution(v)
                        if v_real is not None:
                            activity_to_remove.append(v_real)
                elif isinstance(v, RectangularRegion):
                    if "placingArea" in v.name or "pickingArea" in v.name:
                        rectangle_to_remove.append(v)

        for mc in self.meta_constraints:
            if isinstance(mc, FluentBasedSimpleDomain):
                for v in fluent_to_remove:
                    fluent = cast(SpatialFluent, v)
                    for rr in mc.get_current_reusable_resources_used_by_activity(fluent.activity):
                        rr.remove_usage(fluent.activity)
                for v in activity_to_remove:
                    act = cast("SymbolicVariableActivity", v)
                    for rr in mc.get_current_reusable_resources_used_by_activity(act):
                        rr.remove_usage(act)

        is_retracting_spatial_relations = isinstance(
            meta_value.specialized_annotation, int
        ) and not isinstance(meta_value.specialized_annotation, bool)

        if is_retracting_spatial_relations:
            spatial_fluent_to_be_removed: list[Variable] = []
            self.logger.debug("Meta Value of MetaSpatialConstraint is retracted")

            spatial_fluent_solver = cast(SpatialFluentSolver, self.constraint_solvers[0])
            for var in spatial_fluent_solver.get_variables():
                fluent = cast(SpatialFluent, var)
                if (
                    fluent.activity.temporal_variable.est == 0
                    and fluent.activity.temporal_variable.lst == self.horizon
                ):
                    spatial_fluent_to_be_removed.append(fluent)

            for mc in self.meta_constraints:
                if isinstance(mc, MetaSpatialAdherenceConstraint):
                    for rel in mc.get_s_assertional_rels():
                        rel.unary_at_rectangle_constraint = mc.get_current_assertional_cons()[
                            rel.from_
                        ]
            self.logger.debug("%s", spatial_fluent_to_be_removed)
            spatial_fluent_solver.remove_variables(spatial_fluent_to_be_removed)

        cast(SpatialFluentSolver, self.constraint_solvers[0]).remove_variables(fluent_to_remove)
        ground_solver.remove_variables(activity_to_remove)
        cast(
            RectangleConstraintSolver,
            cast(SpatialFluentSolver, self.constraint_solvers[0]).constraint_solvers[0],
        ).remove_variables(rectangle_to_remove)

    def add_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> bool:
        if meta_value.specialized_annotation is not None and _is_simple_operator(
            meta_value.specialized_annotation
        ):
            if meta_value.specialized_annotation in self.operators_along_branch:
                return False
            self.operators_along_branch.append(meta_value.specialized_annotation)

        # This handles the case where controllables are not unified and no
        # operator can be activated: annotated False to force failure rather
        # than returning a null/empty constraint network.
        if isinstance(meta_value.specialized_annotation, bool):
            if not meta_value.specialized_annotation:
                self.logger.debug(">>>>>>>>>>>>>>>>>")
                return False

        ground_solver = cast(
            ActivityNetworkSolver,
            cast(SpatialFluentSolver, self.constraint_solvers[0]).constraint_solvers[1],
        )

        # Make real variables from variable prototypes.
        for v in meta_value.get_variables():
            if isinstance(v, VariablePrototype):
                # Parameters for real instantiation: the first is the
                # component itself, the second is the symbol of the Activity
                # (or SpatialFluent) to be instantiated.
                component = cast(str, v.parameters[0])
                symbol = cast(str, v.parameters[1])

                if self._manipulation_area_encoding in symbol:
                    sf = cast(
                        SpatialFluent,
                        cast(SpatialFluentSolver, self.constraint_solvers[0]).create_variable(
                            component
                        ),
                    )
                    sf.name = symbol
                    sf.rectangular_region.name = symbol
                    sf.activity.set_symbolic_domain(symbol)
                    sf.activity.marking = v.marking
                    meta_value.add_substitution(v, sf)
                else:
                    tail_activity = cast(
                        "SymbolicVariableActivity", ground_solver.create_variable(component)
                    )
                    tail_activity.set_symbolic_domain(symbol)
                    tail_activity.marking = v.marking
                    meta_value.add_substitution(v, tail_activity)

        # Involve real variables in the constraints. If the constraint
        # involves a manipulationArea prototype, the RectangleConstraint has
        # to be between two RectangularRegions, not between two SpatialFluents.
        for con in list(meta_value.get_constraints()):
            cloned_constraint = con.clone()
            old_scope = con.scope
            new_scope: list[Variable] = [None] * len(old_scope)  # type: ignore[list-item]
            if isinstance(con, AllenIntervalConstraint):
                for i, old_var in enumerate(old_scope):
                    if isinstance(old_var, VariablePrototype):
                        if self._manipulation_area_encoding in cast(str, old_var.parameters[1]):
                            new_scope[i] = cast(
                                SpatialFluent, meta_value.get_substitution(old_var)
                            ).activity
                        else:
                            new_scope[i] = meta_value.get_substitution(old_var)
                    elif isinstance(old_var, SpatialFluent):
                        new_scope[i] = old_var.activity
                    else:
                        new_scope[i] = old_var
            else:  # RectangleConstraint
                for i, old_var in enumerate(old_scope):
                    if isinstance(old_var, VariablePrototype):
                        if self._manipulation_area_encoding in cast(str, old_var.parameters[1]):
                            new_scope[i] = cast(
                                SpatialFluent, meta_value.get_substitution(old_var)
                            ).rectangular_region
                        else:
                            new_scope[i] = meta_value.get_substitution(old_var)
                    elif isinstance(old_var, SpatialFluent):
                        new_scope[i] = old_var.rectangular_region
                    else:
                        new_scope[i] = old_var
            cloned_constraint.scope = new_scope
            meta_value.remove_constraint(con)
            meta_value.add_constraint(cloned_constraint)

        for v in meta_value.get_variables():
            for mc in self.meta_constraints:
                if isinstance(mc, FluentBasedSimpleDomain):
                    for rr in mc.get_current_reusable_resources_used_by_activity(v):
                        rr.set_usage(cast("SymbolicVariableActivity", v))

        return True

    def get_upper_bound(self) -> float:
        return 0.0

    def set_upper_bound(self) -> None:
        pass

    def get_lower_bound(self) -> float:
        return 0.0

    def set_lower_bound(self) -> None:
        pass

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        return False

    def reset_false_clause(self) -> None:
        pass

    def get_old_rectangular_region(self) -> dict[str, BoundingBox] | None:
        for mc in self.meta_constraints:
            if isinstance(mc, MetaSpatialAdherenceConstraint):
                return mc.get_old_rectangular_region()
        return None

    def add_goal(self, act: SymbolicVariableActivity) -> None:
        self._goals.append(act)

    def get_goals(self) -> list[SymbolicVariableActivity]:
        return self._goals

    def add_observation(self, observation: dict[str, object]) -> None:
        self._observation = observation

    def add_observed_spatial_fluents(self, observed_spatial_fluent: SpatialFluent) -> None:
        self._observed_spatial_fluents.append(observed_spatial_fluent)

    def get_observed_spatial_fluents(self) -> list[SpatialFluent]:
        return self._observed_spatial_fluents

    def get_conflict_ranking(self) -> dict[str, int] | None:
        return self._conflict_ranking

    @property
    def manipulation_area_encoding(self) -> str:
        return self._manipulation_area_encoding

    @manipulation_area_encoding.setter
    def manipulation_area_encoding(self, value: str) -> None:
        self._manipulation_area_encoding = value

    def set_obstacles(self, s_assertional_rels: list[SpatialAssertionalRelation]) -> None:
        bbs: list[BoundingBox] = []
        for rel in s_assertional_rels:
            if rel.ontological_prop.is_obstacle:
                b = rel.unary_at_rectangle_constraint.bounds
                bbs.append(BoundingBox(b[0], b[1], b[2], b[3]))
        cast(
            RectangleConstraintSolver,
            cast(SpatialFluentSolver, self.constraint_solvers[0]).constraint_solvers[0],
        ).set_filtering_area(bbs)


def _is_simple_operator(annotation: object) -> bool:
    from metacsp.meta.simple_planner.simple_operator import SimpleOperator

    return isinstance(annotation, SimpleOperator)
