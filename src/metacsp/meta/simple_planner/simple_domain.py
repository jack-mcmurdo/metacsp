"""Port of meta/simplePlanner/SimpleDomain.java.

The ``.ddl`` domain-description grammar is parsed by hand-rolled string
scanning (:meth:`SimpleDomain.parse_keyword`) rather than a generated parser
-- the Java source implements the grammar this way directly (no JavaCC/ANTLR
artifacts were found for this package), so this is a mechanical, not a
structural, port.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.framework.value_ordering_h import ValueOrderingH
from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.framework.variable_prototype import VariablePrototype
from metacsp.meta.simple_planner.planning_operator import PlanningOperator
from metacsp.meta.simple_planner.simple_operator import SimpleOperator
from metacsp.meta.simple_planner.simple_reusable_resource import SimpleReusableResource
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.variable import Variable
    from metacsp.meta.symbols_and_time.schedulable import Schedulable

__all__ = ["SimpleDomain"]


class _MostActivitiesVarOH(VariableOrderingH):
    """Anonymous VariableOrderingH (see Java ``SimpleDomain`` constructor):
    the most critical conflict is the one with the most activities."""

    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        return len(n2.get_variables()) - len(n1.get_variables())

    def collect_data(self, all_meta_variables: object) -> None:
        pass


class _NoOpValOH(ValueOrderingH):
    """Anonymous ValueOrderingH (see Java ``SimpleDomain`` constructor): no
    value ordering."""

    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        return 0


class _AnnotationValOH(ValueOrderingH):
    """Anonymous ValueOrderingH used by :meth:`SimpleDomain.parse_domain`:
    prefer higher-annotation resolvers (unifications carry annotation 2,
    operator expansions 1, unsupported-actuator fallbacks 0), else fewer
    variables."""

    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        if n1.annotation is not None and n2.annotation is not None:
            if isinstance(n1.annotation, int) and isinstance(n2.annotation, int):
                return n2.annotation - n1.annotation
        return len(n1.get_variables()) - len(n2.get_variables())


class _NoOpVarOH(VariableOrderingH):
    """Anonymous VariableOrderingH used by :meth:`SimpleDomain.parse_domain`:
    no variable ordering."""

    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        return 0

    def collect_data(self, all_meta_variables: object) -> None:
        pass


class SimpleDomain(MetaConstraint):
    """The MetaConstraint implementing STRIPS-like hierarchical task
    expansion: MetaVariables are UNJUSTIFIED Activities, and MetaValues are
    either unifications with an existing (justified) Activity or expansions
    via a matching :class:`~.simple_operator.SimpleOperator`/
    :class:`~.planning_operator.PlanningOperator`."""

    class markings(Enum):
        UNJUSTIFIED = auto()
        JUSTIFIED = auto()
        DIRTY = auto()
        STATIC = auto()
        IGNORE = auto()
        PLANNED = auto()
        UNPLANNED = auto()
        PERMANENT = auto()
        OBSERVED_UNJ = auto()
        OBSERVED_JUST = auto()
        IMPOSSIBLE = auto()
        COND_UNJUSTIFIED = auto()
        COND_CURRENT_UNJUSTIFIED = auto()

    def __init__(
        self,
        capacities: list[int],
        resource_names: list[str],
        domain_name: str,
        everything: str | None = None,
    ) -> None:
        super().__init__(None, None)
        self.name = domain_name
        self.resource_names = resource_names
        self.current_resource_utilizers: dict[SimpleReusableResource, dict[Variable, int]] = {}
        self.resources_map: dict[str, SimpleReusableResource] = {}
        self.operators: list[SimpleOperator] = []
        self.everything = everything
        # Java: `protected long filteringTime = Long.MIN_VALUE;`
        self.filtering_time = -(2**63)

        self.sensors: list[str] = []
        self.actuators: list[str] = []
        self.context_vars: list[str] = []
        self.operators_levels: dict[SimpleOperator, int] = {}
        self.unification_track: dict[SymbolicVariableActivity, SymbolicVariableActivity] = {}
        self.timelines: list[str] = []

        for i in range(len(capacities)):
            # Most critical conflict is the one with most activities.
            var_oh: VariableOrderingH = _MostActivitiesVarOH()
            # No value ordering.
            val_oh: ValueOrderingH = _NoOpValOH()
            self.resources_map[resource_names[i]] = SimpleReusableResource(
                var_oh, val_oh, capacities[i], self, resource_names[i]
            )

        # For every SimpleReusableResource just created, couple it with a
        # dict of variable usages.
        for rr in self.resources_map.values():
            self.current_resource_utilizers[rr] = {}

    def get_scheduling_meta_constraints(self) -> list[Schedulable]:
        return list(self.current_resource_utilizers.keys())

    def set_filtering_time(self, filtering_time: int) -> None:
        self.filtering_time = filtering_time

    def add_resource_utilizers(self, rr: SimpleReusableResource, hm: dict[Variable, int]) -> None:
        self.current_resource_utilizers[rr] = hm

    def add_resource_utilizer(self, rr: SimpleReusableResource, var: Variable, amount: int) -> None:
        self.current_resource_utilizers[rr][var] = amount

    def add_resource_map(
        self, resourcename: str, simple_reusable_resource: SimpleReusableResource
    ) -> None:
        self.resources_map[resourcename] = simple_reusable_resource

    def add_operator(self, r: SimpleOperator) -> None:
        self.operators.append(r)

    def get_ground_solver(self) -> ConstraintSolver:
        assert self.meta_cs is not None
        return self.meta_cs.constraint_solvers[0]

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        ground_solver = cast(ActivityNetworkSolver, self.get_ground_solver())
        ret: list[ConstraintNetwork] = []
        # For every variable marked UNJUSTIFIED a ConstraintNetwork is built.
        for task in ground_solver.get_variables():
            if task.marking == SimpleDomain.markings.UNJUSTIFIED:
                nw = ConstraintNetwork(None)
                nw.add_variable(task)
                ret.append(nw)
        return ret

    def expand_operator(
        self, possible_operator: SimpleOperator, problematic_activity: SymbolicVariableActivity
    ) -> ConstraintNetwork:
        activity_network_to_return = ConstraintNetwork(None)
        ground_solver = cast(ActivityNetworkSolver, self.get_ground_solver())

        possible_operator_head = possible_operator.head
        possible_operator_head_symbol = possible_operator_head[
            possible_operator_head.index("::") + 2 :
        ]
        possible_operator_head_component = possible_operator_head[
            : possible_operator_head.index("::")
        ]
        head_activity: Variable | None = None

        problematic_act_is_effect = False
        operator_tail_activities_to_insert: list[Variable] = []

        if possible_operator.requirement_activities is not None:
            operator_tail_activities_to_insert = cast(
                "list[Variable]", [None] * len(possible_operator.requirement_activities)
            )

            for i, possible_operator_tail in enumerate(possible_operator.requirement_activities):
                possible_operator_tail_component = possible_operator_tail[
                    : possible_operator_tail.index("::")
                ]
                possible_operator_tail_symbol = possible_operator_tail[
                    possible_operator_tail.index("::") + 2 :
                ]

                # If this requirement is the problematic activity, insert it directly.
                if (
                    possible_operator_tail_component == problematic_activity.component
                    and possible_operator_tail_symbol
                    == problematic_activity.symbolic_variable.symbols[0]
                ):
                    operator_tail_activities_to_insert[i] = problematic_activity
                    problematic_act_is_effect = True
                # Else make a new VariablePrototype and insert it.
                else:
                    tail_activity = VariablePrototype(
                        ground_solver,
                        possible_operator_tail_component,
                        possible_operator_tail_symbol,
                    )
                    operator_tail_activities_to_insert[i] = tail_activity
                    if isinstance(possible_operator, PlanningOperator):
                        if possible_operator.is_effect(possible_operator_tail):
                            tail_activity.marking = SimpleDomain.markings.JUSTIFIED
                        else:
                            tail_activity.marking = SimpleDomain.markings.UNJUSTIFIED
                    else:
                        tail_activity.marking = SimpleDomain.markings.UNJUSTIFIED

            # Also add the head if the problematic activity was unified with an effect.
            if problematic_act_is_effect:
                head_activity = VariablePrototype(
                    ground_solver, possible_operator_head_component, possible_operator_head_symbol
                )
                head_activity.marking = SimpleDomain.markings.JUSTIFIED

            allen_interval_constraints_to_add: list[AllenIntervalConstraint] = []
            assert possible_operator.requirement_constraints is not None
            for i in range(len(possible_operator.requirement_constraints)):
                rc = possible_operator.requirement_constraints[i]
                if rc is not None:
                    con = cast(AllenIntervalConstraint, rc.clone())
                    if problematic_act_is_effect:
                        con.from_ = head_activity
                    else:
                        con.from_ = problematic_activity
                    con.to = operator_tail_activities_to_insert[i]
                    allen_interval_constraints_to_add.append(con)
            for con in allen_interval_constraints_to_add:
                activity_network_to_return.add_constraint(con)

        to_add_extra: list[AllenIntervalConstraint] = []
        for i in range(len(operator_tail_activities_to_insert) + 1):
            ec = possible_operator.extra_constraints
            if ec is not None:
                con_row = ec[i]
                for j in range(len(con_row)):
                    con = con_row[j]
                    if con is not None:
                        new_con = cast(AllenIntervalConstraint, con.clone())
                        if i == 0:
                            new_con.from_ = (
                                head_activity if problematic_act_is_effect else problematic_activity
                            )
                        else:
                            new_con.from_ = operator_tail_activities_to_insert[i - 1]
                        if j == 0:
                            new_con.to = (
                                head_activity if problematic_act_is_effect else problematic_activity
                            )
                        else:
                            new_con.to = operator_tail_activities_to_insert[j - 1]
                        to_add_extra.append(new_con)

        for v in operator_tail_activities_to_insert:
            activity_network_to_return.add_variable(v)
        if to_add_extra:
            for con in to_add_extra:
                activity_network_to_return.add_constraint(con)

        usages = possible_operator.usages
        if usages is not None:
            for i in range(len(usages)):
                if usages[i] != 0:
                    utilizers = self.current_resource_utilizers[
                        self.resources_map[self.resource_names[i]]
                    ]
                    if problematic_act_is_effect:
                        assert head_activity is not None
                        utilizers[head_activity] = usages[i]
                    else:
                        utilizers[problematic_activity] = usages[i]
                    activity_network_to_return.add_variable(problematic_activity)

        return activity_network_to_return

    def add_sensor(self, sensor: str) -> None:
        self.sensors.append(sensor)

    def add_actuator(self, actuator: str) -> None:
        self.actuators.append(actuator)

    def add_context_var(self, cv: str) -> None:
        self.context_vars.append(cv)

    def is_sensor(self, component: str | None) -> bool:
        return component in self.sensors

    def is_actuator(self, component: str | None) -> bool:
        return component in self.actuators

    def is_context_var(self, component: str | None) -> bool:
        return component in self.context_vars

    def _filter_unifications(
        self, possible_unifications: list[SymbolicVariableActivity]
    ) -> list[SymbolicVariableActivity]:
        return [
            act for act in possible_unifications if act.temporal_variable.let >= self.filtering_time
        ]

    def get_unifications(
        self, activity: SymbolicVariableActivity
    ) -> list[ConstraintNetwork] | None:
        ground_solver = cast(ActivityNetworkSolver, self.get_ground_solver())
        acts = ground_solver.get_variables()

        possible_unifications: list[SymbolicVariableActivity] = []
        for var in acts:
            if var != activity:
                act = cast(SymbolicVariableActivity, var)
                problematic_activity_symbolic_domain = activity.symbolic_variable.symbols[0]
                if act.component == activity.component:
                    act_symbols = act.symbolic_variable.symbols
                    for symbol in act_symbols:
                        if symbol in problematic_activity_symbolic_domain:
                            if act.marking == SimpleDomain.markings.JUSTIFIED:
                                possible_unifications.append(act)
                            break
        return self._get_unifications_from_candidates(
            activity, self._filter_unifications(possible_unifications)
        )

    def _get_unifications_from_candidates(
        self,
        activity: SymbolicVariableActivity,
        possible_unifications: list[SymbolicVariableActivity],
    ) -> list[ConstraintNetwork] | None:
        unifications: list[ConstraintNetwork] = []
        for act in possible_unifications:
            one_unification = ConstraintNetwork(None)
            equals = AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals)
            equals.from_ = activity
            equals.to = act
            one_unification.add_constraint(equals)
            unifications.append(one_unification)
            # Highest priority.
            one_unification.annotation = 2
        if not unifications:
            return None
        return unifications

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        ret_possible_constraint_networks: list[ConstraintNetwork] = []
        problematic_network = meta_variable.constraint_network
        assert problematic_network is not None
        problematic_activity = cast(
            SymbolicVariableActivity, problematic_network.get_variables()[0]
        )

        self.logger.debug("Getting metavalues for %s", problematic_activity)

        operators_cons_network: list[ConstraintNetwork] = []
        unification_cons_network: list[ConstraintNetwork] = []

        # If it's a sensor, it needs to be unified.
        if self.is_sensor(problematic_activity.component):
            self.logger.debug(
                "%s is a Sensor - adding unifications", problematic_activity.component
            )
            unifications = self.get_unifications(problematic_activity)
            if unifications is not None:
                for cn in unifications:
                    cn.annotation = 2
            # But before returning all the unifications (which could be the
            # empty set), also add the expansions of PlanningOperators that
            # have this problematic activity as an AchievedState.
            problematic_activity_symbolic_domain = problematic_activity.symbolic_variable.symbols[0]
            for r in self.operators:
                if isinstance(r, PlanningOperator):
                    assert r.requirement_activities is not None
                    for req_state in r.requirement_activities:
                        operator_effect = req_state
                        operator_effect_component = operator_effect[: operator_effect.index("::")]
                        operator_effect_symbol = operator_effect[operator_effect.index("::") + 2 :]
                        if r.is_effect(req_state):
                            if problematic_activity.component == operator_effect_component:
                                if operator_effect_symbol == problematic_activity_symbolic_domain:
                                    new_resolver = self.expand_operator(r, problematic_activity)
                                    new_resolver.annotation = r
                                    # Middle priority.
                                    new_resolver.annotation = 1
                                    ret_possible_constraint_networks.append(new_resolver)
            if unifications is not None:
                ret_possible_constraint_networks.extend(unifications)
            return ret_possible_constraint_networks

        # Find all expansions.
        for r in self.operators:
            problematic_activity_symbolic_domain = problematic_activity.symbolic_variable.symbols[0]
            operator_head = r.head
            operator_head_component = operator_head[: operator_head.index("::")]
            operator_head_symbol = operator_head[operator_head.index("::") + 2 :]
            if operator_head_component == problematic_activity.component:
                if operator_head_symbol in problematic_activity_symbolic_domain:
                    new_resolver = self.expand_operator(r, problematic_activity)
                    # Middle priority.
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
                                # structural fidelity.
                                new_resolver.annotation = r
                                # Middle priority.
                                new_resolver.annotation = 1
                                ret_possible_constraint_networks.append(new_resolver)

        self.logger.debug("%s is not a Sensor - adding expansions", problematic_activity.component)

        # If it's a context var, it needs to be unified (or expanded, see above).
        if self.is_context_var(problematic_activity.component):
            self.logger.debug(
                "%s is a ContextVariable - adding unifications", problematic_activity.component
            )
            unifications = self.get_unifications(problematic_activity)
            if unifications is not None:
                for one_unification in unifications:
                    ret_possible_constraint_networks.append(one_unification)
                    # Highest priority.
                    one_unification.annotation = 2

        # If it's an actuator, it needs to be unified (or expanded, see above).
        elif self.is_actuator(problematic_activity.component):
            self.logger.debug(
                "%s is an Actuator - adding unifications", problematic_activity.component
            )
            unifications = self.get_unifications(problematic_activity)
            if unifications is not None:
                for one_unification in unifications:
                    ret_possible_constraint_networks.append(one_unification)
                    # Highest priority.
                    one_unification.annotation = 2

        ret_possible_constraint_networks.extend(unification_cons_network)
        ret_possible_constraint_networks.extend(operators_cons_network)

        if not operators_cons_network:
            # Actuator, but no expansions available - so justified by default.
            if self.is_actuator(problematic_activity.component):
                self.logger.debug(
                    "%s is an Actuator but has no available expansions - "
                    "activity is directly supported",
                    problematic_activity.component,
                )
                null_activity_network = ConstraintNetwork(None)
                null_activity_network.specialized_annotation = False
                # Least priority.
                null_activity_network.annotation = 0
                ret_possible_constraint_networks.append(null_activity_network)

        if ret_possible_constraint_networks:
            return ret_possible_constraint_networks
        self.logger.debug("%s HAS NO RESOLVERS, will FAIL!", problematic_activity.component)
        return []

    def mark_resolved_sub(self, meta_variable: MetaVariable, meta_value: ConstraintNetwork) -> None:
        cn = meta_variable.constraint_network
        assert cn is not None
        if cn.get_variables():
            cn.get_variables()[0].marking = SimpleDomain.markings.JUSTIFIED

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def get_resources(self) -> dict[str, SimpleReusableResource]:
        return self.resources_map

    def get_current_reusable_resources_used_by_activity(
        self, act: Variable
    ) -> list[SimpleReusableResource]:
        return [
            rr
            for rr in self.current_resource_utilizers
            if act in self.current_resource_utilizers[rr]
        ]

    def get_resource_usage_level(self, rr: SimpleReusableResource, act: Variable) -> int:
        return self.current_resource_utilizers[rr][act]

    def get_all_resource_usage_level(self) -> dict[SimpleReusableResource, dict[Variable, int]]:
        return self.current_resource_utilizers

    def reset_all_resource_allocation(self) -> None:
        self.current_resource_utilizers = {}
        for rr in self.resources_map.values():
            self.current_resource_utilizers[rr] = {}

    def __str__(self) -> str:
        return f"{type(self).__name__} {self.name}"

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> SimpleDomain | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    @staticmethod
    def instantiate_variable(var: str) -> str:
        return var[var.index("?") :]

    @staticmethod
    def _parse_operator(
        textual_specification: str, resources: list[str], planning_op: bool
    ) -> SimpleOperator:
        required_states: dict[str, str] = {}
        constraints: list[AllenIntervalConstraint] = []
        froms: list[str] = []
        tos: list[str] = []
        resource_requirements: list[int] = [0] * len(resources)
        effects: dict[str, bool] = {}

        head_element = SimpleDomain.parse_keyword("Head", textual_specification)
        head = head_element[0].strip()

        required_state_elements = SimpleDomain.parse_keyword("RequiredState", textual_specification)
        for req_element in required_state_elements:
            req_key = req_element[: req_element.index(" ")].strip()
            req_state = req_element[req_element.index(" ") :].strip()
            required_states[req_key] = req_state
            effects[req_key] = False

        achieved_state_elements = SimpleDomain.parse_keyword("AchievedState", textual_specification)
        for ach_element in achieved_state_elements:
            ach_key = ach_element[: ach_element.index(" ")].strip()
            ach_state = ach_element[ach_element.index(" ") :].strip()
            required_states[ach_key] = ach_state
            effects[ach_key] = True

        constraint_elements = SimpleDomain.parse_keyword("Constraint", textual_specification)
        for con_element in constraint_elements:
            bounds: list[Bounds] | None = None
            if "[" in con_element:
                constraint_name = con_element[: con_element.index("[")].strip()
                bounds_string = con_element[con_element.index("[") : con_element.rindex("]") + 1]
                split_bounds = bounds_string.split("[")
                bounds = []
                for one_bound in split_bounds:
                    if one_bound.strip() != "":
                        lb_idx = one_bound.find("[")
                        lb_string = one_bound[lb_idx + 1 : one_bound.index(",")].strip()
                        ub_string = one_bound[
                            one_bound.index(",") + 1 : one_bound.index("]")
                        ].strip()
                        lb: int
                        ub: int
                        if lb_string == "INF":
                            lb = APSPSolver.INF
                        elif lb_string.startswith("?"):
                            lb = int(SimpleDomain.instantiate_variable(lb_string))
                        else:
                            lb = int(lb_string)
                        if ub_string == "INF":
                            ub = APSPSolver.INF
                        elif ub_string.startswith("?"):
                            ub = int(SimpleDomain.instantiate_variable(ub_string))
                        else:
                            ub = int(ub_string)
                        bounds.append(Bounds(lb, ub))
            else:
                constraint_name = con_element[: con_element.index("(")].strip()

            from_: str
            to: str
            if constraint_name == "Duration":
                from_ = con_element[con_element.index("(") + 1 : con_element.index(")")].strip()
                to = from_
            else:
                from_seg = con_element[con_element.index("(") :]
                from_ = from_seg[from_seg.index("(") + 1 : from_seg.index(",")].strip()
                to = from_seg[from_seg.index(",") + 1 : from_seg.index(")")].strip()

            con_type = AllenIntervalConstraint.Type[constraint_name]
            con: AllenIntervalConstraint
            if bounds is not None:
                con = AllenIntervalConstraint(con_type, *bounds)
            else:
                con = AllenIntervalConstraint(con_type)
            constraints.append(con)
            froms.append(from_)
            tos.append(to)

        resource_elements = SimpleDomain.parse_keyword("RequiredResource", textual_specification)
        for res_element in resource_elements:
            required_resource = res_element[: res_element.index("(")].strip()
            required_amount = int(
                res_element[res_element.index("(") + 1 : res_element.index(")")].strip()
            )
            for k in range(len(resources)):
                if resources[k] == required_resource:
                    resource_requirements[k] = required_amount

        # What I have:
        # constraints = {During, Duration, Before}
        # froms = {Head, Head, req1}
        # tos = {req1, Head, req2}
        # requirements = {req2 = Robot1::At(room), req1 = Robot1::MoveTo()}

        requirement_strings: list[str] = [""] * len(required_states)
        effect_bools: list[bool] = [False] * len(required_states)
        cons_from_head_to_req: list[AllenIntervalConstraint | None] = [None] * len(required_states)
        additional_constraints: list[tuple[AllenIntervalConstraint, int, int]] = []
        req_keys_to_indices: dict[str, int] = {}

        req_counter = 0
        for req_key, requirement in required_states.items():
            requirement_strings[req_counter] = requirement
            req_keys_to_indices[req_key] = req_counter
            if planning_op:
                effect_bools[req_counter] = bool(effects.get(req_key))
            req_counter += 1

        for i in range(len(froms)):
            # Head -> Head
            if froms[i] == "Head" and tos[i] == "Head":
                additional_constraints.append((constraints[i], 0, 0))
            # req -> req
            elif froms[i] != "Head" and tos[i] != "Head":
                req_from_index = req_keys_to_indices[froms[i]]
                req_to_index = req_keys_to_indices[tos[i]]
                additional_constraints.append(
                    (constraints[i], req_from_index + 1, req_to_index + 1)
                )
            # req -> Head
            elif froms[i] != "Head" and tos[i] == "Head":
                req_from_index = req_keys_to_indices[froms[i]]
                additional_constraints.append((constraints[i], req_from_index + 1, 0))
            # Head -> req
            elif froms[i] == "Head" and tos[i] != "Head":
                cons_from_head_to_req[req_keys_to_indices[tos[i]]] = constraints[i]

        ret: SimpleOperator
        if not planning_op:
            ret = SimpleOperator(
                head, cons_from_head_to_req, requirement_strings, resource_requirements
            )
        else:
            ret = PlanningOperator(
                head,
                cons_from_head_to_req,
                requirement_strings,
                effect_bools,
                resource_requirements,
            )
        for con, from_idx, to_idx in additional_constraints:
            ret.add_constraint(con, from_idx, to_idx)
        return ret

    @staticmethod
    def parse_keyword(keyword: str, everything: str) -> list[str]:
        elements: list[str] = []
        last_element = everything.rfind(keyword)
        while last_element != -1:
            bw = last_element
            fw = last_element
            skip = False
            while True:
                bw -= 1
                ch = everything[bw]
                if ch == "(":
                    break
                if ch != " ":
                    everything = everything[:bw]
                    last_element = everything.rfind(keyword)
                    skip = True
                    break
            if not skip:
                parcounter = 1
                while parcounter != 0:
                    if everything[fw] == "(":
                        parcounter += 1
                    elif everything[fw] == ")":
                        parcounter -= 1
                    fw += 1
                element = everything[bw:fw].strip()
                element = element[
                    element.index(keyword) + len(keyword) : element.rindex(")")
                ].strip()
                if not element.startswith(",") and element.strip() != "":
                    elements.append(element)
                everything = everything[:bw]
                last_element = everything.rfind(keyword)
        return elements

    @staticmethod
    def process_resources(resources: list[str]) -> dict[str, int]:
        ret: dict[str, int] = {}
        for resource_element in resources:
            resource_name = resource_element[: resource_element.index(" ")].strip()
            resource_cap = int(resource_element[resource_element.index(" ") :].strip())
            ret[resource_name] = resource_cap
        return ret

    def parse_user_keyword(self, keyword: str) -> list[str]:
        """Parse a user-defined keyword in the domain, in the form
        ``(UserKeyword value1 [value2 ... valueN])``."""
        assert self.everything is not None
        return SimpleDomain.parse_keyword(keyword, self.everything)

    @staticmethod
    def parse_domain(
        sp: MetaConstraintSolver, filename: str, domain_type: type
    ) -> SimpleDomain | None:
        """Parse a domain file (see ``tests/data/domains/testSimplePlanner.ddl``
        for an example), instantiate the necessary MetaConstraints, and add
        them to the given SimplePlanner."""
        # Local imports to avoid module cycles: ProactivePlanningDomain (M16)
        # and FluentBasedSimpleDomain (M18) both subclass SimpleDomain.
        from metacsp.meta.simple_planner.proactive_planning_domain import ProactivePlanningDomain
        from metacsp.meta.hybrid_planner.fluent_based_simple_domain import FluentBasedSimpleDomain

        logger = get_logger(SimpleDomain)
        try:
            with open(filename, "r") as f:
                lines = f.readlines()
        except OSError as e:
            logger.error("Could not read domain file %s: %s", filename, e)
            return None

        sb: list[str] = []
        for line in lines:
            if not line.strip().startswith("#"):
                sb.append(line if line.endswith("\n") else line + "\n")
        everything = "".join(sb)

        name = SimpleDomain.parse_keyword("Domain", everything)[0]
        resource_elements = SimpleDomain.parse_keyword("Resource", everything)
        resources = SimpleDomain.process_resources(resource_elements)
        simple_operators = SimpleDomain.parse_keyword("SimpleOperator", everything)
        planning_operators = SimpleDomain.parse_keyword("PlanningOperator", everything)
        sensors = SimpleDomain.parse_keyword("Sensor", everything)
        actuators = SimpleDomain.parse_keyword("Actuator", everything)
        context_vars = SimpleDomain.parse_keyword("ContextVariable", everything)

        timelines_string = SimpleDomain.parse_keyword("TimelinesToShow", everything)
        timelines: list[str] | None = None
        if timelines_string:
            timelines = timelines_string[0].split()

        resource_names = list(resources.keys())
        resource_caps = [resources[n] for n in resource_names]

        logger.debug("domain_type=%s", domain_type)
        dom: SimpleDomain | None = None
        if domain_type is SimpleDomain:
            dom = SimpleDomain(resource_caps, resource_names, name, everything)
        elif domain_type is ProactivePlanningDomain:
            dom = ProactivePlanningDomain(resource_caps, resource_names, name, everything)
        elif domain_type is FluentBasedSimpleDomain:
            dom = FluentBasedSimpleDomain(resource_caps, resource_names, name, everything)

        if dom is None:
            return None

        # Return unifications first, then higher-priority expansions.
        dom.val_oh = _AnnotationValOH()
        # No variable ordering.
        dom.var_oh = _NoOpVarOH()

        for sensor in sensors:
            dom.add_sensor(sensor)
        for act in actuators:
            dom.add_actuator(act)
        for cv in context_vars:
            dom.add_context_var(cv)
        for operator in simple_operators:
            dom.add_operator(SimpleDomain._parse_operator(operator, resource_names, False))
        for operator in planning_operators:
            dom.add_operator(SimpleDomain._parse_operator(operator, resource_names, True))

        # ... and we also add all its resources as separate meta-constraints.
        for sch in dom.get_scheduling_meta_constraints():
            sp.add_meta_constraint(sch)

        # This adds the domain as a meta-constraint of the SimplePlanner.
        sp.add_meta_constraint(dom)
        if timelines is not None:
            for timeline in timelines:
                dom._add_timeline(timeline)

        return dom

    def _add_timeline(self, timeline: str) -> None:
        self.timelines.append(timeline)
