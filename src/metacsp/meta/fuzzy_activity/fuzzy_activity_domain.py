"""Port of meta/fuzzyActivity/FuzzyActivityDomain.java.

Implements the MetaConstraint for fuzzy context recognition. MetaVariables
are unjustified :class:`~metacsp.multi.fuzzy_activity.fuzzy_activity.
FuzzyActivity` rule heads; MetaValues are unifications of a Rule's
Requirements with existing FuzzyActivity variables.

Several methods here (``add_rule``, ``add_fuzzy_sensor_events``,
``get_meta_values``, ``set_rule_dependency``, ...) reference the
``org.metacsp.onLineMonitoring`` classes ``Rule``, ``Requirement``,
``Sensor``, ``PhysicalSensor``, and ``FuzzySensorEvent`` -- these are M20
(``metacsp/online_monitoring/``), not yet ported. Per the M16 task scope
this file ports ``FuzzyActivityDomain`` itself; the onLineMonitoring types
are referenced only as ``TYPE_CHECKING``-only forward imports (never
evaluated at runtime, since this module uses ``from __future__ import
annotations``) pointing at their anticipated M20 module paths, and are
accessed at runtime purely via duck-typed attribute access following this
codebase's C2 naming convention (e.g. Java's ``Rule.getComponent()`` is
expected to become a Python ``Rule.component`` property once M20 lands).
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity
from metacsp.multi.fuzzy_activity.fuzzy_activity_network_solver import FuzzyActivityNetworkSolver
from metacsp.multi.fuzzy_activity.simple_timeline import SimpleTimeline
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.utility.math import PermutationsWithRepetition

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.variable import Variable

    # M20 (not yet ported); see module docstring.
    from metacsp.online_monitoring.fuzzy_sensor_event import FuzzySensorEvent
    from metacsp.online_monitoring.physical_sensor import PhysicalSensor
    from metacsp.online_monitoring.requirement import Requirement
    from metacsp.online_monitoring.rule import Rule
    from metacsp.online_monitoring.sensor import Sensor

__all__ = ["FuzzyActivityDomain"]


def _index_or_neg1(items: list, item: object) -> int:
    """Mirror Java's ``List.indexOf``: -1 if ``item`` is not present."""
    try:
        return items.index(item)
    except ValueError:
        return -1


class FuzzyActivityDomain(MetaConstraint):
    """A MetaConstraint for fuzzy context recognition: variables are rules
    in this "domain", values are unifications of rule requirements with
    existing FuzzyActivity variables."""

    class markings(Enum):
        """A FuzzyActivity representing a hypothesis can be justified or
        not. Unjustified activities are the meta-variables returned by
        :meth:`get_meta_variables`."""

        UNJUSTIFIED = auto()
        JUSTIFIED = auto()

    def __init__(self) -> None:
        super().__init__(None, None)
        self.solver = FuzzyActivityNetworkSolver()
        self.rules: list[Rule] = []
        self.ongoing_acts: list[FuzzyActivity] = []
        self.truth_maintenance_constraints: list[FuzzyAllenIntervalConstraint] = []
        self.timelines: dict[str, SimpleTimeline] = {}
        self.rule_heads: dict[FuzzyActivity, Rule] = {}
        self.fas: list[FuzzyActivity] = []
        # Includes rule heads and sensors.
        self.ground_activity: list[FuzzyActivity] = []
        # Includes rule heads.
        self.heads: list[FuzzyActivity] = []
        self.to_skip: list[Rule] = []

    def _rule_dependency_finder(self) -> None:
        has_dep = False
        for r in self.rules:
            if r not in self.to_skip:
                for req in r.requirements:
                    # Java bug reproduced verbatim: this compares Sensor
                    # name *strings* with `==` (Java reference equality),
                    # not `.equals()` -- almost always False unless the two
                    # strings happen to be the same interned object.
                    # Python's `is` operator mirrors that behavior.
                    if r.component.name is req.sensor.name:
                        if not self._is_fired_before(req):
                            has_dep = True
                        self.logger.debug("%s", r.component.name)
                if not has_dep:
                    self.to_skip.append(r)
            has_dep = False
        if len(self.to_skip) != len(self.rules):
            self._rule_dependency_finder()

    def set_rule_dependency(self) -> None:
        self._rule_dependency_finder()

        domain = self

        class _ToSkipOrderVarOH(VariableOrderingH):
            def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
                a0 = cast(FuzzyActivity, n1.get_variables()[0])
                a1 = cast(FuzzyActivity, n2.get_variables()[0])
                return _index_or_neg1(domain.to_skip, domain.rule_heads[a0]) - _index_or_neg1(
                    domain.to_skip, domain.rule_heads[a1]
                )

            def collect_data(self, all_meta_variables: object) -> None:
                pass

        self.var_oh = _ToSkipOrderVarOH()

    def _is_fired_before(self, req: Requirement) -> bool:
        for r in self.to_skip:
            if self._compare_possibility_degree(r, req):
                return True
        return False

    def _compare_possibility_degree(self, r: Rule, req: Requirement) -> bool:
        for i in range(len(req.possibilities)):
            if req.possibilities[i] != r.possibilities[i]:
                return False
        return True

    def set_unjustified(self, meta_variable: ConstraintNetwork) -> None:
        for v in meta_variable.get_variables():
            v.marking = FuzzyActivityDomain.markings.UNJUSTIFIED

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        ret: list[ConstraintNetwork] = []
        for f in self.fas:
            if f.marking == FuzzyActivityDomain.markings.UNJUSTIFIED:
                fan = ConstraintNetwork(None)
                fan.add_variable(f)
                ret.append(fan)
        return ret

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        conflict = meta_variable.constraint_network
        assert conflict is not None
        constraints: list[list[ConstraintNetwork]] = []
        head = cast(FuzzyActivity, conflict.get_variables()[0])
        sensor_variables: dict[Sensor, list[Variable]] = {}

        rule = self.rule_heads[head]

        for req in rule.requirements:
            sens = req.sensor
            if sensor_variables.get(sens) is None:
                vec: list[Variable] = []
                vars_ = self.solver.get_variables(sens.name)
                if vars_ is not None:
                    for var in vars_:
                        vec.append(var)
                    sensor_variables[sens] = vec

        for req in rule.requirements:
            sens = req.sensor
            vec1 = sensor_variables.get(sens, [])
            vec = [v for v in vec1 if v in self.ground_activity]

            unifications: list[ConstraintNetwork] = []
            for sens_var in vec:
                sens_act = cast(FuzzyActivity, sens_var)
                one_unification = ConstraintNetwork(None)

                # Make temporal constraint (from: head, to: sensAct) of type req.t_cons.
                tcon = FuzzyAllenIntervalConstraint(req.t_cons)
                tcon.from_ = head
                tcon.to = sens_act

                # Make value requirement and corresponding value constraint
                # (from: reqValue, to: sensAct) of type req.v_cons.
                req_value = cast(FuzzyActivity, self.solver.create_variable(sens.name))
                req_value.set_domain(sens.states, req.possibilities)
                req_value_con = SymbolicValueConstraint(req.v_cons)
                req_value_con.from_ = req_value
                req_value_con.to = sens_act

                one_unification.add_variable(head)
                one_unification.add_variable(sens_act)
                one_unification.add_constraint(tcon)
                one_unification.add_variable(req_value)
                one_unification.add_constraint(req_value_con)

                unifications.append(one_unification)
            constraints.append(unifications)

        to_attempt: list[ConstraintNetwork] = []
        max_ = 0
        for vcn in constraints:
            if len(vcn) > max_:
                max_ = len(vcn)

        gen = PermutationsWithRepetition(max_, len(constraints))

        for combination in gen.get_variations():
            skip = False
            for i in range(len(combination)):
                if len(constraints[i]) <= combination[i]:
                    skip = True
                    break
            if not skip:
                one_attempt = ConstraintNetwork(None)
                for i in range(len(combination)):
                    unifs = constraints[i]
                    one_attempt.join(unifs[combination[i]])
                to_attempt.append(one_attempt)

        return to_attempt

    def mark_resolved_sub(self, meta_variable: MetaVariable, meta_value: ConstraintNetwork) -> None:
        cn = meta_variable.constraint_network
        assert cn is not None
        cn.get_variables()[0].marking = FuzzyActivityDomain.markings.JUSTIFIED

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def add_rule(self, r: Rule) -> None:
        self.rules.append(r)
        head = cast(FuzzyActivity, self.solver.create_variable(r.component.name))
        head.marking = FuzzyActivityDomain.markings.UNJUSTIFIED
        head.set_domain(r.component.states, r.possibilities)
        self.rule_heads[head] = r
        self.fas.append(head)
        self.ground_activity.append(head)
        self.heads.append(head)

    def add_fuzzy_sensor_events(self, *events: FuzzySensorEvent) -> None:
        for e in events:
            self._update_sensor_data(e)
        for var in self.solver.get_variables():
            self.ground_activity.append(cast(FuzzyActivity, var))
        self._set_crisp_cons()

    def _update_sensor_data(self, event: FuzzySensorEvent) -> None:
        sensor = event.sensor
        possibilities = event.possibilities
        old_act = sensor.current_act
        sensor.solver = self.solver
        if self.timelines.get(sensor.name) is None:
            self.timelines[sensor.name] = SimpleTimeline(sensor.name)
        first_on_timeline = old_act is None

        tcon = sensor.set_current_possibilities(possibilities)

        act = sensor.current_act

        to_retract: list[FuzzyAllenIntervalConstraint] = []
        to_add: list[FuzzyAllenIntervalConstraint] = []

        if tcon is not None:
            to_add.append(tcon)
            tl = self.timelines[sensor.name]
            if old_act is not None:
                tl.set_end(old_act, event.time)
            tl.add_variable(act)
            tl.set_start(act, event.time)
            if old_act is not None and old_act in self.ongoing_acts:
                self.ongoing_acts.remove(old_act)
            self.ongoing_acts.append(act)

        if first_on_timeline:
            tl = self.timelines[sensor.name]
            tl.add_variable(act)
            tl.set_start(act, event.time)
            self.ongoing_acts.append(act)

        Type = FuzzyAllenIntervalConstraint.Type
        for ongoing in list(self.ongoing_acts):
            if ongoing != act:
                fc_new = FuzzyAllenIntervalConstraint(Type.Finishes, Type.During, Type.OverlappedBy)
                fc_new.from_ = act
                fc_new.to = ongoing
                to_add.append(fc_new)
                self.truth_maintenance_constraints.append(fc_new)

        if tcon is not None:
            no_longer_to_maintain: list[FuzzyAllenIntervalConstraint] = []
            for con in self.truth_maintenance_constraints:
                if con.from_ == old_act:
                    to_retract.append(con)
                    no_longer_to_maintain.append(con)
                    fc_new = FuzzyAllenIntervalConstraint(Type.During)
                    fc_new.from_ = old_act
                    fc_new.to = con.to
                    to_add.append(fc_new)
                elif con.to == old_act:
                    to_retract.append(con)
                    no_longer_to_maintain.append(con)
                    fc_new = FuzzyAllenIntervalConstraint(Type.Overlaps)
                    fc_new.from_ = old_act
                    fc_new.to = con.from_
                    to_add.append(fc_new)
            for con in no_longer_to_maintain:
                self.truth_maintenance_constraints.remove(con)

        if to_retract:
            self.solver.remove_constraints(to_retract)
        if to_add:
            self.solver.add_constraints(*to_add)

    def get_consistency(self) -> float:
        return min(self.solver.get_temporal_consistency(), self.solver.get_value_consistency())

    def get_constraint_network(self) -> ConstraintNetwork:
        return self.solver.constraint_network

    def get_false_clause(self) -> list[Constraint]:
        return self.solver.get_false_clause()

    def reset_false_clause(self) -> None:
        self.solver.reset_false_clauses()

    def _set_crisp_cons(self) -> None:
        self.solver.set_crisp_cons(self.solver.get_constraints())

    def get_optimal_hypothesis(self, opt_cn: ConstraintNetwork, vc: float, tc: float) -> str:
        s = "["
        for var in opt_cn.get_variables():
            for head in self.heads:
                if var.id == head.id:
                    s += self.rule_heads[head].head + " "
        s += "] = " + " Value Consistency: " + str(vc) + " Temporal Consistency: " + str(tc)
        return s

    def get_value_consistency(self) -> float:
        return self.solver.get_value_consistency()

    def get_temporal_consistency(self) -> float:
        return self.solver.get_temporal_consistency()

    def __str__(self) -> str:
        # Java's toString() is an unfinished "TODO Auto-generated method
        # stub" that returns null; Python's __str__ must return str, so this
        # substitutes the class name (matching the sibling Schedulable
        # subclasses' precedent, e.g. StateVariable/Floor2D).
        return type(self).__name__

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> FuzzyActivityDomain | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def get_ground_solver(self) -> ConstraintSolver | None:
        return None
