"""Port of meta/hybridPlanner/FluentBasedSimpleDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.variable_prototype import VariablePrototype
from metacsp.meta.hybrid_planner._rule_utils import (
    fresh_binary_constraint,
    fresh_unary_size_constraint,
)
from metacsp.meta.hybrid_planner._sort_utils import sort_dict_by_value
from metacsp.meta.hybrid_planner.manipulation_area_domain import ManipulationAreaDomain
from metacsp.meta.simple_planner.planning_operator import PlanningOperator
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent import SpatialFluent
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver import SpatialFluentSolver

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.variable import Variable
    from metacsp.meta.simple_planner.simple_operator import SimpleOperator
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity

__all__ = ["FluentBasedSimpleDomain"]


class FluentBasedSimpleDomain(SimpleDomain):
    """A :class:`~metacsp.meta.simple_planner.simple_domain.SimpleDomain`
    whose UNJUSTIFIED activities may also be SpatialFluents: expanding a
    ``RobotAction`` operator that involves a manipulation-area fluent also
    attaches a spatial resolver network (:meth:`get_spatial_constraint_net`)
    computed from the fixed :class:`~.manipulation_area_domain.ManipulationAreaDomain`
    knowledge."""

    def __init__(
        self,
        capacities: list[int],
        resource_names: list[str],
        domain_name: str,
        everything: str | None = None,
    ) -> None:
        super().__init__(capacities, resource_names, domain_name, everything)
        self.manipulation_area_domain = ManipulationAreaDomain()
        self._active_free_arm_heuristic = False
        self._time_now = -1
        self._obj_params: list[str] = []

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        ground_solver = self.get_ground_solver()
        tasks: list[Variable] = []
        opr_parameter: dict[Variable, str] = {}
        for task in ground_solver.get_variables():
            if task.marking == SimpleDomain.markings.UNJUSTIFIED:
                tasks.append(task)
                opr_parameter[task] = self._get_parameter(task)

        from metacsp.meta.hybrid_planner.simple_hybrid_planner import SimpleHybridPlanner

        planner = cast(SimpleHybridPlanner, self.meta_cs)
        conflict_ranking = planner.get_conflict_ranking()
        if conflict_ranking is not None:
            sorted_conflict: dict[ConstraintNetwork, int] = {}
            for task in opr_parameter:
                nw = ConstraintNetwork(None)
                nw.add_variable(task)
                sorted_conflict[nw] = conflict_ranking.get(opr_parameter[task], 0)
            sorted_conflict = sort_dict_by_value(sorted_conflict)
            return list(sorted_conflict.keys())

        ret: list[ConstraintNetwork] = []
        for task in tasks:
            nw = ConstraintNetwork(None)
            nw.add_variable(task)
            ret.append(nw)
        return ret

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        ret_possible_constraint_networks: list[ConstraintNetwork] = []
        problematic_network = meta_variable.constraint_network
        assert problematic_network is not None
        problematic_activity = cast(
            "SymbolicVariableActivity", problematic_network.get_variables()[0]
        )

        operators_cons_network: list[ConstraintNetwork] = []
        unification_cons_network: list[ConstraintNetwork] = []

        # If it's a sensor, it needs to be unified.
        if self.is_sensor(problematic_activity.component):
            return self.get_unifications(problematic_activity) or []

        # If it's a controllable actuator, it needs to be unified (or
        # expanded, see below).
        if self.is_actuator(problematic_activity.component):
            unifications = self.get_unifications(problematic_activity)
            if unifications is not None:
                for cn in unifications:
                    unified_act: SymbolicVariableActivity | None = None
                    for var in cn.get_variables():
                        act = cast("SymbolicVariableActivity", var)
                        if act != problematic_activity:
                            unified_act = act
                    if unified_act not in self.unification_track:
                        unification_cons_network.append(cn)
                        self.unification_track[problematic_activity] = cast(
                            "SymbolicVariableActivity", unified_act
                        )

        # If it's a context var, it needs to be unified (or expanded, see below).
        if self.is_context_var(problematic_activity.component):
            unifications = self.get_unifications(problematic_activity)
            if unifications is not None:
                self.logger.debug("lenght: %d", len(unifications))
                for one_unification in unifications:
                    ret_possible_constraint_networks.append(one_unification)
                    one_unification.annotation = 2

        manipulation_area_prototype: VariablePrototype | None = None

        # Find all expansions.
        for r in self.operators:
            problematic_activity_symbolic_domain = problematic_activity.symbolic_variable.symbols[0]
            operator_head = r.head
            operator_head_component = operator_head[: operator_head.index("::")]
            operator_head_symbol = operator_head[operator_head.index("::") + 2 :]
            if operator_head_component == problematic_activity.component:
                if operator_head_symbol in problematic_activity_symbolic_domain:
                    new_resolver = self.expand_operator(r, problematic_activity)
                    for var in new_resolver.get_variables():
                        if isinstance(var, VariablePrototype):
                            symbol = cast(str, var.parameters[1])
                            if "at_robot1_manipulationArea" in symbol:
                                manipulation_area_prototype = var
                                break
                    new_resolver.annotation = 1
                    new_resolver.specialized_annotation = r
                    operators_cons_network.append(new_resolver)

            if isinstance(r, PlanningOperator):
                assert r.requirement_activities is not None
                for req_state in r.requirement_activities:
                    operator_effect = req_state
                    operator_effect_component = operator_effect[: operator_effect.index("::")]
                    operator_effect_symbol = operator_effect[operator_effect.index("::") + 2 :]
                    if r.is_effect(req_state):
                        if operator_effect_component == problematic_activity.component:
                            if operator_effect_symbol in problematic_activity_symbolic_domain:
                                new_resolver = self.expand_operator(r, problematic_activity)
                                # Java sets .annotation = r here then
                                # immediately overwrites it with 1 below --
                                # dead code, reproduced verbatim for
                                # structural fidelity (see simple_domain.py's
                                # identical note).
                                new_resolver.annotation = r
                                new_resolver.annotation = 1
                                ret_possible_constraint_networks.append(new_resolver)

        if problematic_activity.component == "RobotAction":
            if manipulation_area_prototype is not None:
                spatial_constraint_net = self._get_spatial_constraint_net(
                    problematic_activity, manipulation_area_prototype
                )
                if spatial_constraint_net is None:
                    operators_cons_network[-1].specialized_annotation = False
                else:
                    operators_cons_network[-1].join(spatial_constraint_net)

        # Java resets the heuristic flag immediately before testing it, so
        # the `else` branch below is unreachable in the current source --
        # reproduced verbatim (a real Java quirk, not a typo: see M18
        # nomenclature-audit notes).
        self._active_free_arm_heuristic = False
        if not self._active_free_arm_heuristic:
            ret_possible_constraint_networks.extend(unification_cons_network)
            ret_possible_constraint_networks.extend(operators_cons_network)
        else:
            ret_possible_constraint_networks.extend(unification_cons_network)
            sorted_resolvers: dict[ConstraintNetwork, int] = {}
            for cn in operators_cons_network:
                if cn.specialized_annotation is not None:
                    sorted_resolvers[cn] = self.operators_levels[cn.specialized_annotation]
            sorted_resolvers = sort_dict_by_value(sorted_resolvers)
            ret_possible_constraint_networks.extend(sorted_resolvers.keys())

        if ret_possible_constraint_networks:
            return ret_possible_constraint_networks
        if self.is_actuator(problematic_activity.component):
            null_activity_network = ConstraintNetwork(None)
            null_activity_network.specialized_annotation = False
            return [null_activity_network]
        return [ConstraintNetwork(None)]

    def _get_spatial_constraint_net(
        self,
        problematic_activity: SymbolicVariableActivity,
        manipulation_area_prototype: VariablePrototype,
    ) -> ConstraintNetwork | None:
        ret = ConstraintNetwork(None)
        main_string = problematic_activity.symbolic_variable.symbols[0]
        # e.g. place_cup1_RA_west_table
        obj = self._get_parameter(problematic_activity)

        last_index = main_string.rindex("_")
        arm_and_direction = main_string[main_string.index(obj) + len(obj) + 1 : last_index]
        supporter = main_string[last_index + 1 : len(main_string) - 2]  # e.g. table1

        # We can extract the relevant spatial fluent in two ways: based on
        # the temporal or spatial relation. For spatial: bounded rectangles
        # are those in the future, unbounded ones in the past.
        object_fluent: SpatialFluent | None = None
        support_fluent: SpatialFluent | None = None
        is_place = True
        spatial_fluent_solver = cast(SpatialFluentSolver, self.meta_cs.constraint_solvers[0])  # type: ignore[union-attr]
        for var in spatial_fluent_solver.get_variables():
            temp_fluent = cast(SpatialFluent, var)
            if temp_fluent.name == f"at_{supporter}_{supporter}":
                support_fluent = temp_fluent
            if "pick" in main_string:
                if (
                    temp_fluent.name == f"at_{obj}_{supporter}"
                    and temp_fluent.activity.temporal_variable.est
                    == temp_fluent.activity.temporal_variable.lst
                ):
                    # It is observed, but it has to be the last spatial
                    # fluent which has this property (online pick and place).
                    object_fluent = temp_fluent
                    is_place = False
            elif "place" in main_string:
                if (
                    temp_fluent.name == f"at_{obj}_{supporter}"
                    and temp_fluent.activity.temporal_variable.est
                    != temp_fluent.activity.temporal_variable.lst
                ):
                    object_fluent = temp_fluent

        if object_fluent is None:
            return None

        all_constraints: list[object] = []
        srules = self.manipulation_area_domain.get_spatial_rules_by_relation(arm_and_direction)

        rec_solver = cast("ConstraintSolver", spatial_fluent_solver.constraint_solvers[0])
        placing_rec_var = cast(RectangularRegion, rec_solver.create_variable())
        placing_rec_var.name = (
            f"placingArea_{obj}_{arm_and_direction}"
            if is_place
            else f"pickingArea_{obj}_{arm_and_direction}"
        )
        ret.add_variable(placing_rec_var)

        # ------------------------------------------------------------------
        # Creating the spatial constraints. The order is fixed and based on
        # the fixed order ManipulationAreaDomain defines its rules in:
        # "manipulationArea"/"manipulationArea", "placingArea"/"placingArea",
        # "placingArea"/"manipulationArea", "object"/"placingArea",
        # "manipulationArea"/"table".
        # ------------------------------------------------------------------
        size_manipulation_area = fresh_unary_size_constraint(srules[0])
        size_manipulation_area.from_ = manipulation_area_prototype
        size_manipulation_area.to = manipulation_area_prototype
        all_constraints.append(size_manipulation_area)

        size_placing_area = fresh_unary_size_constraint(srules[1])
        size_placing_area.from_ = placing_rec_var
        size_placing_area.to = placing_rec_var
        all_constraints.append(size_placing_area)

        manipulation_area_to_table = fresh_binary_constraint(srules[4])
        manipulation_area_to_table.from_ = manipulation_area_prototype
        assert support_fluent is not None
        manipulation_area_to_table.to = support_fluent.rectangular_region
        all_constraints.append(manipulation_area_to_table)

        # We already know the order of the rules from ManipulationAreaDomain.
        placing_area_to_manipulation_area = fresh_binary_constraint(srules[2])
        placing_area_to_manipulation_area.from_ = placing_rec_var
        placing_area_to_manipulation_area.to = manipulation_area_prototype
        all_constraints.append(placing_area_to_manipulation_area)

        object_to_placing_area = fresh_binary_constraint(srules[3])
        object_to_placing_area.from_ = object_fluent.rectangular_region
        object_to_placing_area.to = placing_rec_var
        all_constraints.append(object_to_placing_area)

        skip = False
        # Add an At constraint if the fluent belongs to the past: it affects
        # how MetaOccupiedConstraint works.
        if object_fluent.rectangular_region.is_unbounded():
            from metacsp.meta.hybrid_planner.simple_hybrid_planner import SimpleHybridPlanner

            old_rectangular_region = cast(
                SimpleHybridPlanner, self.meta_cs
            ).get_old_rectangular_region()
            if old_rectangular_region is not None:
                for name, unbound_bb in old_rectangular_region.items():
                    if object_fluent.name == name:
                        at_obj_instance = UnaryRectangleConstraint(
                            UnaryRectangleConstraint.Type.At,
                            unbound_bb.x_lb,
                            unbound_bb.x_ub,
                            unbound_bb.y_lb,
                            unbound_bb.y_ub,
                        )
                        at_obj_instance.from_ = object_fluent
                        at_obj_instance.to = object_fluent
                        all_constraints.append(at_obj_instance)
            else:
                skip = True

        if not skip:
            for con in all_constraints:
                ret.add_constraint(con)  # type: ignore[arg-type]

        return ret

    def _get_parameter(self, task: Variable) -> str:
        sym = cast("SymbolicVariableActivity", task).symbolic_variable.symbols[0]
        if "hold" in sym:
            if sym.rindex("_") == sym.index("_"):
                ret = sym[sym.index("_") : sym.index("(")] + "_table1"
            else:
                ret = sym[sym.index("_") + 6 : sym.index("(")] + "_table1"
        elif "sensing" in sym:
            ret = sym[sym.index("_") + 16 : sym.index("(")]
        elif "manipulationArea" in sym:
            ret = sym[sym.index("_") + 25 : sym.index("(")]
        else:
            first_ = sym[sym.index("_") + 1 :]
            ret = first_[: first_.index("_")]
        return ret

    def get_ground_solver(self) -> ConstraintSolver:
        return cast(
            "ConstraintSolver",
            cast(SpatialFluentSolver, self.meta_cs.constraint_solvers[0]).constraint_solvers[1],  # type: ignore[union-attr]
        )

    def update_time_now(self, time_now: int) -> None:
        self._time_now = time_now

    def active_heuristic(self, active: bool) -> None:
        self._active_free_arm_heuristic = active

    def apply_free_arm_heuristic(
        self,
        var_involved_in_occupied_meta_constraints: list[SymbolicVariableActivity],
        heuristic_term: str,
    ) -> None:
        self._obj_params = []
        for act in var_involved_in_occupied_meta_constraints:
            sym = act.symbolic_variable.symbols[0]
            param = sym[sym.index("_") + 1 : sym.index("_", sym.index("_") + 1)]
            self._obj_params.append(param)

        params_to_operators: dict[str, list[SimpleOperator]] = {}
        for param in self._obj_params:
            ops = [op for op in self.operators if param in op.head]
            params_to_operators[param] = ops

        for param, ops in params_to_operators.items():
            for op in ops:
                if self._has_operator(op, heuristic_term):
                    self.operators_levels[op] = 0
                else:
                    self.operators_levels[op] = 1

        for op in self.operators:
            if op not in self.operators_levels:
                self.operators_levels[op] = 2

    def _has_operator(self, simple_operator: SimpleOperator, heuristic_term: str) -> bool:
        if heuristic_term in simple_operator.head:
            return True
        if simple_operator.requirement_activities is not None:
            for req in simple_operator.requirement_activities:
                if heuristic_term in req:
                    return True
        return False
