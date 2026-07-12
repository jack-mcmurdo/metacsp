"""Port of onLineMonitoring/DomainDescription.java.

The central class of online monitoring: holds a set of
:class:`~metacsp.online_monitoring.rule.Rule`\\ s, feeds sensor readings
(:class:`~metacsp.online_monitoring.fuzzy_sensor_event.FuzzySensorEvent`) to
a :class:`~metacsp.multi.fuzzy_activity.fuzzy_activity_network_solver
.FuzzyActivityNetworkSolver`, and evaluates each Rule's requirements against
current readings to produce ranked
:class:`~metacsp.online_monitoring.hypothesis.Hypothesis` objects.

There is no Java JUnit test or example for this package (verified against
the pinned Java commit); the class's behavior here -- including several
upstream bugs -- was derived entirely from reading ``DomainDescription
.java``'s method bodies. Two upstream bugs are reproduced verbatim (see the
inline comments at their sites): (1) ``getBestHypotheses`` always reads back
element 0 of its accumulator instead of element 0 of the current rule's
result; (2) ``getMaxTimeline``'s trailing "best node" scan has a loop
condition that can never iterate. A third, in ``stopMonitoring``'s shutdown
poll, is *not* reproduced because it is an infinite loop (once any thread is
observed alive, the exit flag latches false forever) that would hang the
ported method in real dispatch-simulation usage; see the comment at its
site for the one-line fix applied instead.
"""

from __future__ import annotations

import threading
import time as _time
from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity
from metacsp.multi.fuzzy_activity.fuzzy_activity_network_solver import FuzzyActivityNetworkSolver
from metacsp.multi.fuzzy_activity.simple_timeline import SimpleTimeline
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.online_monitoring.hypothesis import Hypothesis
from metacsp.online_monitoring.hypothesis_node import HypothesisNode
from metacsp.time.bounds import Bounds
from metacsp.utility.logging import get_logger
from metacsp.utility.math import PermutationsWithRepetition

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.online_monitoring.fuzzy_sensor_event import FuzzySensorEvent
    from metacsp.online_monitoring.hypothesis_listener import HypothesisListener
    from metacsp.online_monitoring.rule import Rule
    from metacsp.online_monitoring.sensor import Sensor

__all__ = ["DomainDescription"]

Type = FuzzyAllenIntervalConstraint.Type


class DomainDescription:
    """A set of monitoring :class:`~metacsp.online_monitoring.rule.Rule`\\ s
    driven by a stream of :class:`~metacsp.online_monitoring
    .fuzzy_sensor_event.FuzzySensorEvent`\\ s."""

    class OPTIONS(Enum):
        SIMULATE_SENSOR_DISPATCH = auto()
        NO_SENSOR_DISPATCH = auto()

    class TIMELINE_OPTION(Enum):
        """Java ``TIMELINEOPION`` (misspelling of "TIMELINEOPTION"),
        corrected here per C2; declared but never used upstream (its one
        use site is commented out in the Java source)."""

        MAX_OVERALL_CONSISTENCY = auto()
        MAX_TEMPORAL_CONSISTENCY = auto()
        MAX_VALUE_CONSISTENCY = auto()

    def __init__(self, *rules: Rule) -> None:
        self.solver = FuzzyActivityNetworkSolver()
        self.rules: list[Rule] = []
        self.ongoing_acts: list[FuzzyActivity] = []
        self.truth_maintenance_constraints: list[FuzzyAllenIntervalConstraint] = []
        self.clock_start = -1
        self.fast_forward = True
        self.timelines: dict[str, SimpleTimeline] = {}
        self.fixed_hypotheses: list[Hypothesis] = []
        self.fixed_networks: list[ConstraintNetwork] = []
        self.sensors: dict[str, Sensor] = {}
        self.optimize = False
        self.to_skip: list[Rule] = []

        # Java bug reproduced verbatim (flagged upstream by the authors
        # themselves via a FindBugs FIXME comment): this field's initializer
        # runs before the constructor body assigns `solver` (Java runs
        # instance-field initializers in declaration order, then the
        # constructor body), so it is always built against a null solver --
        # mirrored here by passing None regardless of self.solver above.
        self.inferred_hypotheses = ConstraintNetwork(None)

        self.hl: HypothesisListener | None = None
        self.threshold = -1.0
        self.max_hypotheses = -1
        self.stopped = True
        self.paused = False
        self.pause_start = 0
        self.pause_delta = 0
        self.current_pass = 1

        # "Iran" hierarchical-inference bookkeeping (ghost-sensor hypothesis
        # dependency graph); see add_fuzzy_inferred_events/get_max_timeline.
        self.timelinestate = True
        self.first_layer: list[int] = []
        self.hyp_nodes: list[HypothesisNode] = []
        self.ground_sensors: list[FuzzyActivity] = []
        self.first_call = False
        self.hnodeshmap: dict[FuzzyActivity, HypothesisNode] = {}
        self.crisp_cons: list[FuzzyAllenIntervalConstraint] = []

        self.threads: list[threading.Thread] | None = None
        self._critical_section = threading.RLock()
        self.logger = get_logger(type(self))

        self._set_rules(list(rules))
        self.clock_start = self._now_ms()
        for r in rules:
            self._register_rule_sensors(r)
        self.first_layer.append(-1)

    # --- construction helpers ---

    @staticmethod
    def _now_ms() -> int:
        return int(_time.time() * 1000)

    def _register_rule_sensors(self, r: Rule) -> None:
        for req in r.requirements:
            sens = req.sensor
            assert sens is not None
            sens.solver = self.solver
            if sens.name not in self.sensors:
                self.sensors[sens.name] = sens
            if sens.name not in self.timelines:
                self.timelines[sens.name] = SimpleTimeline(sens.name)

    def add_rule(self, r: Rule) -> None:
        self.rules = self.rules + [r]
        self._register_rule_sensors(r)

    def add_rules(self, rules: list[Rule]) -> None:
        self._set_rules(list(rules))
        for r in rules:
            self._register_rule_sensors(r)

    def _set_rules(self, rules: list[Rule]) -> None:
        self.rules = rules

    # --- clock / lifecycle ---

    def start_monitoring(self) -> None:
        self.stopped = False
        if not self.fast_forward:
            self.threads = []
        self.clock_start = self._now_ms()

    def stop_monitoring(self) -> None:
        self.stopped = True
        if not self.fast_forward:
            # Java resets nothing inside this poll loop, so once any thread
            # is observed alive its `checkStopped` flag latches false
            # forever and the loop never exits again, even after every
            # thread has since finished -- an infinite-loop defect, not an
            # "obvious typo"; reproducing it verbatim would hang this
            # method whenever SIMULATE_SENSOR_DISPATCH threads were ever
            # started, so it is fixed here by re-checking aliveness fresh
            # on every pass instead of latching a single failed check.
            while any(t.is_alive() for t in (self.threads or [])):
                _time.sleep(0.1)
        self.clock_start = -1

    def pause_monitoring(self) -> None:
        if not self.paused:
            self.pause_start = self._now_ms() - self.pause_delta
            self.paused = True

    def resume_monitoring(self) -> None:
        if self.paused:
            with self._critical_section:
                self.pause_delta = self._now_ms() - self.pause_start
                self.paused = False

    @property
    def time(self) -> int:
        if self.paused:
            return (self.pause_start - self.clock_start) // 1000
        return ((self._now_ms() - self.pause_delta) - self.clock_start) // 1000

    def set_options(self, opt: DomainDescription.OPTIONS) -> None:
        if opt == DomainDescription.OPTIONS.SIMULATE_SENSOR_DISPATCH:
            self.fast_forward = False
        elif opt == DomainDescription.OPTIONS.NO_SENSOR_DISPATCH:
            self.fast_forward = True

    @property
    def constraint_network(self) -> ConstraintNetwork:
        return self.solver.constraint_network

    # --- sensor-waiting thread (D9) ---

    def _start_sensor_waiting_thread(self, event: FuzzySensorEvent) -> None:
        def _run() -> None:
            while (
                self._now_ms() - self.pause_delta
            ) - self.clock_start < event.time * 1000 or self.paused:
                if self.stopped:
                    break
                _time.sleep(0.1)
            if not self.stopped:
                self._update_sensor_data(event)
                self._trigger_hypothesis_listener()

        t = threading.Thread(target=_run, daemon=True)
        if self.threads is not None:
            self.threads.append(t)
        t.start()

    # --- hypothesis production ---

    def get_best_hypotheses(self, max: int) -> list[Hypothesis]:
        """Java ``getBestHypotheses(int max)`` overload: the top ``max``
        (highest overall-consistency) hypotheses per not-yet-skipped rule."""
        ret: list[Hypothesis] = []
        best_set: list[Hypothesis] = []
        for r in self.rules:
            if r not in self.to_skip:
                one_rule = self._get_consistency(r)
                if one_rule is not None:
                    one_rule = sorted(one_rule)
                    for i in range(min(len(one_rule), max)):
                        ret.append(one_rule[i])
                    # Java bug reproduced verbatim: reads ret[0] (the first
                    # hypothesis ever appended across *all* rules processed
                    # so far), not oneRule[0] for the current rule.
                    best = ret[0]
                    best_set.append(best)
        if best_set:
            for best in best_set:
                self.add_fuzzy_inferred_events(best)
                self.to_skip.append(best.rule)
            self.current_pass += 1
            self._trigger_hypothesis_listener()
        return ret

    def get_best_hypotheses_over_threshold(self, threshold: float) -> list[Hypothesis]:
        """Java ``getBestHypotheses(double threshold)`` overload: all
        hypotheses (per not-yet-skipped rule, sorted best-first) down to the
        first one below ``threshold``."""
        ret: list[Hypothesis] = []
        best_set: list[Hypothesis] = []
        for r in self.rules:
            if r not in self.to_skip:
                one_rule = self._get_consistency(r)
                if one_rule is not None:
                    one_rule = sorted(one_rule)
                    for h in one_rule:
                        if h.overall_consistency >= threshold:
                            ret.append(h)
                        else:
                            break
                    best = ret[0]
                    best_set.append(best)
        if best_set:
            for best in best_set:
                self.add_fuzzy_inferred_events(best)
            self._trigger_hypothesis_listener()
        return ret

    def get_max_timeline(self) -> list[Hypothesis]:
        """Make a pruned graph from all possible hypotheses and find the
        maximum path that includes an instance of each hypothesis (not
        necessarily the maximum one). ("Iran".)"""
        ret: list[Hypothesis] = []
        best_set: list[Hypothesis] = []
        if not self.first_call:
            for v in self.variables:
                self.ground_sensors.append(cast(FuzzyActivity, v))
            self.first_call = True

        for r in self.rules:
            if r not in self.to_skip:
                one_rule = self._get_consistency(r)
                if one_rule is not None:
                    for h in one_rule:
                        if h.overall_consistency > r.threshold:
                            ret.append(h)
                            best_set.append(h)

        if best_set:
            for best in best_set:
                self.add_fuzzy_inferred_events(best)
                self.to_skip.append(best.rule)
            self.current_pass += 1
            self._trigger_hypothesis_listener()

        # Java bug reproduced verbatim: `bestNode` is read unconditionally,
        # so with zero ghost-sensor hypotheses ever recorded (hyp_nodes
        # empty -- the common case unless a rule's head is also consumed as
        # a "_"-prefixed ghost sensor by another rule) this raises, exactly
        # as Java's ArrayIndexOutOfBoundsException would. The scan below it
        # decrements from `len(hyp_nodes) - 2`, whose loop condition
        # (`i < 0`) can only be true when it starts negative, so for
        # `len(hyp_nodes) >= 2` it never iterates (dead code, as upstream).
        best_node = self.hyp_nodes[len(self.hyp_nodes) - 1]
        i = len(self.hyp_nodes) - 2
        while i < 0:
            if self.hyp_nodes[i].hyp.pass_ == self.current_pass:
                if self.hyp_nodes[i].sigma_oc > best_node.sigma_oc:
                    best_node = self.hyp_nodes[i]
            i -= 1
        # best_node is computed, matching Java, but (as upstream) never
        # used afterwards -- its only consumer is a commented-out debug
        # print block in the Java source.

        return ret

    def add_fuzzy_inferred_events(self, best: Hypothesis) -> None:
        ghost_sensor = self.sensors.get("_" + best.rule.component.name)
        if ghost_sensor is not None:
            poss = best.rule.possibilities
            for i in range(len(poss)):
                if poss[i] != 0.0:
                    poss[i] = best.overall_consistency
            dependencies: list[FuzzyActivity] = []
            with self._critical_section:
                act = cast(FuzzyActivity, self.solver.create_variable(ghost_sensor.name))
                act.set_domain(ghost_sensor.states, poss)
                self.inferred_hypotheses.add_variable(act)
                cons = best.constraint_network.get_constraints()

                has_head = 0
                for con in cons:
                    old_scope = con.scope
                    if old_scope[0] == best.head:
                        has_head += 1
                    else:
                        dependencies.append(cast(FuzzyActivity, old_scope[0]))
                    if old_scope[1] == best.head:
                        has_head -= 1
                    else:
                        dependencies.append(cast(FuzzyActivity, old_scope[1]))

                    if has_head == 1:
                        contmp = FuzzyAllenIntervalConstraint(
                            *cast(FuzzyAllenIntervalConstraint, con).types
                        )
                        contmp.from_ = act
                        contmp.to = old_scope[1]
                        self.solver.add_constraints(contmp)
                        self.inferred_hypotheses.add_constraint(contmp)
                    elif has_head == -1:
                        contmp = FuzzyAllenIntervalConstraint(
                            *cast(FuzzyAllenIntervalConstraint, con).types
                        )
                        contmp.from_ = old_scope[1]
                        contmp.to = act
                        self.solver.add_constraints(contmp)
                        self.inferred_hypotheses.add_constraint(contmp)
                    has_head = 0

                tl = self.timelines[ghost_sensor.name]
                tl.add_variable(act)
                interval = best.get_interval(self.timelines)
                tl.set_start(act, interval.min)
                tl.set_end(act, interval.max)

                act.is_hypothesis = True
                act.dependencies = dependencies

                sigma_tc = best.temporal_consistency
                sigma_vc = best.value_consistency
                sigma_oc = best.overall_consistency
                for dep in dependencies:
                    if dep.is_hypothesis:
                        node = self.hnodeshmap[dep]
                        sigma_tc += node.sigma_tc
                        sigma_vc += node.sigma_vc
                        sigma_oc += node.sigma_oc

                hn = HypothesisNode(act, sigma_tc, sigma_vc, sigma_oc, best)
                self.hyp_nodes.append(hn)
                self.hnodeshmap[act] = hn

    def add_fuzzy_sensor_events(self, *events: FuzzySensorEvent) -> None:
        if self.to_skip:
            self.to_skip = []
            cons = self.inferred_hypotheses.get_constraints()
            vars_ = self.inferred_hypotheses.get_variables()
            self.solver.remove_constraints(cons)
            self.solver.remove_variables(vars_)
            self.inferred_hypotheses = ConstraintNetwork(self.solver)

        if not self.fast_forward:
            for e in events:
                self._start_sensor_waiting_thread(e)
        else:
            for e in events:
                self._update_sensor_data(e)
            self._trigger_hypothesis_listener()

    def _trigger_hypothesis_listener(self) -> None:
        if self.hl is not None:
            hypotheses: list[Hypothesis] | None = None
            if self.timelinestate:
                hypotheses = self.get_max_timeline()
            elif self.threshold != -1.0:
                hypotheses = self.get_best_hypotheses_over_threshold(self.threshold)
            elif self.max_hypotheses != -1:
                hypotheses = self.get_best_hypotheses(self.max_hypotheses)
            if hypotheses is not None:
                self.hl(hypotheses)

    def _update_sensor_data(self, e: FuzzySensorEvent) -> None:
        with self._critical_section:
            sensor = e.sensor
            possibilities = e.possibilities
            old_act = sensor.current_act

            first_on_timeline = old_act is None

            # If changed then tcon will be != None.
            tcon = sensor.set_current_possibilities(possibilities)

            act = sensor.current_act

            to_retract: list[FuzzyAllenIntervalConstraint] = []
            to_add: list[FuzzyAllenIntervalConstraint] = []

            if tcon is not None:
                to_add.append(tcon)
                tl = self.timelines[sensor.name]
                if old_act is not None:
                    tl.set_end(old_act, e.time)
                tl.add_variable(act)
                tl.set_start(act, e.time)
                if old_act is not None:
                    self.ongoing_acts.remove(old_act)
                self.ongoing_acts.append(act)

            if first_on_timeline:
                tl = self.timelines[sensor.name]
                tl.add_variable(act)
                tl.set_start(act, e.time)
                self.ongoing_acts.append(act)

            # add act --{FINISHES v DURING v OVERLAPPEDBY}--> [all ongoing]
            for ongoing in self.ongoing_acts:
                if ongoing != act:
                    fc_new = FuzzyAllenIntervalConstraint(
                        Type.Finishes, Type.During, Type.OverlappedBy
                    )
                    fc_new.from_ = act
                    fc_new.to = ongoing
                    to_add.append(fc_new)
                    self.truth_maintenance_constraints.append(fc_new)

            if tcon is not None:
                no_longer_to_maintain: list[FuzzyAllenIntervalConstraint] = []
                for con in self.truth_maintenance_constraints:
                    # if oldAct started later than x (and since oldAct is
                    # now finished and x continues) remove oldAct
                    # --{FINISHES v DURING v OVERLAPPEDBY}--> x, add oldAct
                    # --DURING--> x
                    if con.from_ == old_act:
                        to_retract.append(con)
                        no_longer_to_maintain.append(con)
                        fc_new = FuzzyAllenIntervalConstraint(Type.During)
                        fc_new.from_ = old_act
                        fc_new.to = con.to
                        to_add.append(fc_new)
                    # if oldAct started earlier than x, i.e. oldAct
                    # --{FINISHEDBY v CONTAINS v OVERLAPS}--> x: remove x
                    # --{FINISHES v DURING v OVERLAPPEDBY}--> oldAct, add
                    # oldAct --OVERLAPS--> x
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
                self.solver.remove_constraints(cast("list[Constraint]", to_retract))
            if to_add:
                self.crisp_cons.extend(to_add)
                self.solver.add_constraints(*to_add)

    def _get_consistency(self, r: Rule) -> list[Hypothesis] | None:
        """Temporal and symbolic degrees of satisfaction of ``r`` against
        current sensor readings, as one Hypothesis per possible unification
        of its requirements with those readings."""
        with self._critical_section:
            impossible_req = False
            ret: list[Hypothesis] = []

            if self.optimize:
                ret.extend(self.fixed_hypotheses)

            component = r.component
            head = cast(FuzzyActivity, self.solver.create_variable(component.name))
            head.set_domain(component.states, r.possibilities)

            constraints: list[list[ConstraintNetwork]] = []
            cleanup_acts: list[FuzzyActivity] = [head]
            sensor_variables: dict[Sensor, list[Variable]] = {}

            for req in r.requirements:
                sens = req.sensor
                assert sens is not None
                if sens not in sensor_variables:
                    vars_ = self.solver.get_variables(sens.name)
                    if vars_ is not None:
                        sensor_variables[sens] = list(vars_)

            dependencies_fz_act: list[FuzzyActivity] = []
            marks_as_general_req: list[FuzzyActivity] = []

            for req in r.requirements:
                sens = req.sensor
                assert sens is not None
                vec = sensor_variables.get(sens)
                if vec is None:
                    impossible_req = True
                    break
                sens_vars = list(vec)
                unifications: list[ConstraintNetwork] = []
                for sens_var in sens_vars:
                    sens_act = cast(FuzzyActivity, sens_var)
                    one_unification = ConstraintNetwork(None)

                    tcon = FuzzyAllenIntervalConstraint(req.t_cons)
                    tcon.from_ = head
                    tcon.to = sens_act

                    req_value = cast(FuzzyActivity, self.solver.create_variable(sens.name))
                    req_value.set_domain(sens.states, req.possibilities)
                    req_value_con = SymbolicValueConstraint(req.v_cons)
                    req_value_con.set_from(req_value)
                    req_value_con.set_to(sens_act)

                    if sens_act.is_hypothesis:
                        dependencies_fz_act.append(sens_act)
                    marks_as_general_req.append(req_value)
                    marks_as_general_req.append(head)

                    one_unification.add_variable(head)
                    one_unification.add_variable(sens_act)
                    one_unification.add_constraint(tcon)
                    one_unification.add_variable(req_value)
                    one_unification.add_constraint(req_value_con)

                    cleanup_acts.append(req_value)
                    unifications.append(one_unification)
                constraints.append(unifications)

            new_fixed_networks: list[ConstraintNetwork] | None = None
            if self.optimize:
                new_fixed_networks = []

            if not impossible_req:
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

                        if self.optimize:
                            assert new_fixed_networks is not None
                            filtered = ConstraintNetwork(None)
                            for v in one_attempt.get_variables():
                                if (
                                    self.solver.get_component(v) in self.sensors
                                    and v not in cleanup_acts
                                ):
                                    filtered.add_variable(v)
                            if filtered not in self.fixed_networks:
                                to_attempt.append(one_attempt)
                                all_fixed = True
                                for var in filtered.get_variables():
                                    if var in self.ongoing_acts:
                                        all_fixed = False
                                if all_fixed:
                                    self.fixed_networks.append(filtered)
                                    new_fixed_networks.append(one_attempt)
                        else:
                            to_attempt.append(one_attempt)

                if not to_attempt:
                    for v in cleanup_acts:
                        self.solver.remove_variable(v)
                    return None

                for cn in to_attempt:
                    to_propagate = cn.get_constraints()

                    marks_as_sens_req: list[FuzzyActivity] = []
                    if self.current_pass > 1:
                        for con in to_propagate:
                            self._extract_dependencies(
                                marks_as_sens_req, cast(FuzzyActivity, con.scope[0])
                            )
                            self._extract_dependencies(
                                marks_as_sens_req, cast(FuzzyActivity, con.scope[1])
                            )
                        marks_as_sens_req.extend(marks_as_general_req)
                        marks_as_sens_req.extend(self.ground_sensors)
                        self.solver.set_var_of_sub_graph(marks_as_sens_req)
                        self.solver.set_crisp_cons(cast("list[Constraint]", self.crisp_cons))

                    self.solver.add_constraints(*to_propagate)
                    marks_as_sens_req.clear()

                    tc = self.solver.get_temporal_consistency()
                    vc = self.solver.get_value_consistency()
                    h = Hypothesis(tc, vc, cn, r, head, self.current_pass)
                    ret.append(h)

                    if (
                        self.optimize
                        and new_fixed_networks is not None
                        and cn in new_fixed_networks
                    ):
                        self.fixed_hypotheses.append(h)

                    self.solver.remove_constraints(cast("list[Constraint]", list(to_propagate)))

            for v in cleanup_acts:
                self.solver.remove_variable(v)

            if impossible_req:
                return None

            return ret

    def _extract_dependencies(
        self, marks_as_sens_req: list[FuzzyActivity], fa: FuzzyActivity
    ) -> None:
        if len(fa.dependencies) == 0:
            return
        if fa not in marks_as_sens_req:
            marks_as_sens_req.append(fa)
        for dep in fa.dependencies:
            if dep not in marks_as_sens_req:
                marks_as_sens_req.append(dep)
                self._extract_dependencies(marks_as_sens_req, dep)

    def draw_network(self) -> None:
        """Java draws the solver's ConstraintNetwork in a Swing window here;
        the UI is out of scope (see the plan's skip list; a replacement
        live viewer arrives in M21), so this only logs the request."""
        self.logger.info("draw_network() requested; drawing is not ported (see M21).")

    def get_timeline(self, s: Sensor) -> SimpleTimeline | None:
        return self.timelines.get(s.name)

    def get_timelines(self) -> list[SimpleTimeline]:
        return list(self.timelines.values())

    def get_min_interval(self, h: Hypothesis) -> Bounds:
        return h.get_interval(self.timelines)

    def register_hypothesis_listener(self, hl: HypothesisListener, threshold: float) -> None:
        """Java ``registerHypothesisListener(HypothesisListener, double)``
        overload."""
        self.hl = hl
        self.threshold = threshold
        self.max_hypotheses = -1

    def register_hypothesis_listener_for_max(
        self, hl: HypothesisListener, max_hypotheses: int
    ) -> None:
        """Java ``registerHypothesisListener(HypothesisListener, int)``
        overload."""
        self.hl = hl
        self.threshold = -1.0
        self.max_hypotheses = max_hypotheses

    @property
    def variables(self) -> list[Variable]:
        return self.solver.get_variables()

    @property
    def constraints(self) -> list[Constraint]:
        return self.solver.get_constraints()
