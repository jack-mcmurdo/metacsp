"""Port of meta/hybridPlanner/MetaSpatialAdherenceConstraint.java.

Two Java-source idioms are deliberately *not* reproduced literally, with
reasoning kept close to the code that would otherwise hide it:

* ``permutation`` (Java: ``HashMap<HashMap<String, Bounds[]>, Integer>``) and
  ``rank`` (Java: ``HashMap<Vector<UnaryRectangleConstraint>, Integer>``) use
  a *mutable* Java object as a map key. Analysis of the construction sites
  shows every key object is freshly allocated with never-shared nested
  arrays/constraints, so Java's (structural) HashMap equality never actually
  collapses two distinct entries there -- both maps behave as plain ordered
  association lists in practice. This port represents them as such
  (``list[tuple[key, value]]``), which is both simpler and avoids inventing
  Python hashability for non-hashable dict/list keys.
* ``samplingPeakCollection``'s inner ``overlapping`` ``Vector`` is mutated
  in place across loop iterations while also being stored by *reference*
  into ``overlappingAll`` each time a conflict is detected -- meaning, per
  outer iteration, every stored entry actually aliases the same
  (later-mutated) object and so ends up reflecting its *final* accumulated
  state, not a snapshot at detection time. This reads as an accidental
  aliasing artifact of Java's reference semantics rather than an intended
  behavior; this port stores an explicit snapshot (``list(overlapping)``)
  at each detection instead, matching the algorithm's evident intent
  (record the overlapping set *as observed when the conflict was found*).
"""

from __future__ import annotations

import functools
from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.framework.multi.multi_binary_constraint import MultiBinaryConstraint
from metacsp.multi.activity.activity_comparator import ActivityComparator
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.multi.spatial.rectangle_algebra.bounding_box import BoundingBox
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint_solver import (
    RectangleConstraintSolver,
)
from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent import SpatialFluent
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver import SpatialFluentSolver
from metacsp.meta.hybrid_planner._rule_utils import (
    fresh_binary_constraint,
    fresh_unary_size_constraint,
)
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.utility.math import PermutationsWithRepetition, PowerSet

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.spatial.utility.spatial_assertional_relation import SpatialAssertionalRelation
    from metacsp.spatial.utility.spatial_rule import SpatialRule

__all__ = ["MetaSpatialAdherenceConstraint"]

_AT = UnaryRectangleConstraint.Type.At


def _equals_constraint() -> RectangleConstraint:
    eq = AllenIntervalConstraint.Type.Equals
    return RectangleConstraint(AllenIntervalConstraint(eq), AllenIntervalConstraint(eq))


def _at_constraint(bounds: tuple[Bounds, Bounds, Bounds, Bounds]) -> UnaryRectangleConstraint:
    return UnaryRectangleConstraint(_AT, *(Bounds(b.min, b.max) for b in bounds))


class MetaSpatialAdherenceConstraint(MetaConstraint):
    """A MetaConstraint checking that the current placement of movable
    objects (SpatialFluents) adheres to a fixed set of general spatial
    knowledge (:class:`~metacsp.spatial.utility.spatial_rule.SpatialRule`)
    plus the current assertional relations
    (:class:`~metacsp.spatial.utility.spatial_assertional_relation.SpatialAssertionalRelation`),
    generating a ranked set of alternative placements (goals) for whichever
    objects are the culprit of an inconsistency."""

    class PEAKCOLLECTION(Enum):
        SAMPLING = auto()
        COMPLETE = auto()
        BINARY = auto()

    def __init__(self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None) -> None:
        super().__init__(var_oh, val_oh)
        self.origin = 0
        self.horizon = 1000
        self._s_assertional_rels: list[SpatialAssertionalRelation] = []
        self.rules: list[SpatialRule] | None = None
        self._permutation: list[tuple[dict[str, list[Bounds]], int]] = []
        self._initial_unbounded_obj_name: list[str] = []
        self._potential_culprit: list[str] = []
        self._current_assertional_cons: dict[str, UnaryRectangleConstraint] = {}
        self._old_rectangular_region: dict[str, BoundingBox] | None = None
        self._total_time = 0
        self._conflict_tracking: list[list[int]] = []
        # Java's ``manAreaResource`` field is declared but never assigned or
        # read anywhere in the class -- dead state, kept for structural
        # fidelity only.
        self._man_area_resource = None
        self._number_of_misplaced = 0
        self.before_parameter = 1
        self.peak_collection_strategy = MetaSpatialAdherenceConstraint.PEAKCOLLECTION.SAMPLING

    # --- simple accessors -------------------------------------------------

    def get_culprit_detection_time(self) -> int:
        return self._total_time

    def get_number_of_misplaced(self) -> int:
        return self._number_of_misplaced

    def get_current_assertional_cons(self) -> dict[str, UnaryRectangleConstraint]:
        return self._current_assertional_cons

    def get_old_rectangular_region(self) -> dict[str, BoundingBox] | None:
        return self._old_rectangular_region

    def set_spatial_rules(self, *rules: SpatialRule) -> None:
        self.rules = list(rules)

    def set_spatial_assertional_relations(
        self, s_assertional_rels: list[SpatialAssertionalRelation]
    ) -> None:
        self._s_assertional_rels = list(s_assertional_rels)

    def get_s_assertional_rels(self) -> list[SpatialAssertionalRelation]:
        return self._s_assertional_rels

    def _get_potential_culprit(self) -> list[str]:
        return self._potential_culprit

    def set_initial_goal(self, initial_goals: list[str]) -> None:
        self._initial_unbounded_obj_name.extend(initial_goals)

    @staticmethod
    def power_set(original_set: list) -> list[list]:
        """Delegates to :class:`metacsp.utility.math.PowerSet` -- the Java
        source re-derives the identical recursive algorithm locally instead
        of reusing ``utility/PowerSet.java``; this port reuses the one
        already-ported implementation (see module docstring)."""
        return PowerSet.power_set(original_set)

    # --- general spatial knowledge helper (shared across 3 Java methods) --

    def _general_knowledge_constraints(
        self, solver: ConstraintSolver, get_variable_by_name: dict[str, RectangularRegion]
    ) -> list[MultiBinaryConstraint]:
        assert self.rules is not None
        added: list[MultiBinaryConstraint] = []
        for rule in self.rules:
            con: MultiBinaryConstraint
            if rule.from_ == rule.to:
                con = fresh_unary_size_constraint(rule)
            else:
                con = fresh_binary_constraint(rule)
            con.from_ = self._region_for(rule.from_, solver, get_variable_by_name)
            con.to = self._region_for(rule.to, solver, get_variable_by_name)
            added.append(con)
        return added

    @staticmethod
    def _region_for(
        name: str, solver: ConstraintSolver, get_variable_by_name: dict[str, RectangularRegion]
    ) -> RectangularRegion:
        region = get_variable_by_name.get(name)
        if region is None:
            region = cast(RectangularRegion, solver.create_variable())
            region.name = name
            get_variable_by_name[name] = region
        return region

    def _create_tbox_spatial_network(
        self, solver: ConstraintSolver, get_variable_by_name: dict[str, RectangularRegion]
    ) -> ConstraintNetwork:
        ret = ConstraintNetwork(solver)
        for con in self._general_knowledge_constraints(solver, get_variable_by_name):
            ret.add_constraint(con)
        return ret

    # --- peak collection ----------------------------------------------------

    def _sampling_peak_collection(
        self, a_to_sf: dict[SymbolicVariableActivity, SpatialFluent]
    ) -> list[ConstraintNetwork]:
        activities = list(a_to_sf.keys())
        observation = [
            act for act in activities if act.temporal_variable.est == act.temporal_variable.lst
        ]
        if not activities:
            return []

        ground_vars = sorted(activities, key=functools.cmp_to_key(ActivityComparator(True).compare))
        ret: list[ConstraintNetwork] = []
        overlapping_all: list[list[SymbolicVariableActivity]] = []

        # An activity spatially inconsistent even with itself.
        for act in activities:
            if self.is_conflicting([act], a_to_sf):
                temp = ConstraintNetwork(None)
                temp.add_variable(act)
                ret.append(temp)

        for i in range(len(ground_vars)):
            overlapping = [ground_vars[i]]
            intersection = Bounds(
                ground_vars[i].temporal_variable.est, ground_vars[i].temporal_variable.eet
            )
            for j in range(len(ground_vars)):
                if i == j:
                    continue
                next_interval = Bounds(
                    ground_vars[j].temporal_variable.est, ground_vars[j].temporal_variable.eet
                )
                intersection_new = intersection.intersect_strict(next_interval)
                if intersection_new is not None:
                    overlapping.append(ground_vars[j])
                    if self.is_conflicting(overlapping, a_to_sf):
                        overlapping_all.append(list(overlapping))  # snapshot; see module note
                        if all(o in overlapping for o in observation):
                            break
                    else:
                        intersection = intersection_new

        if overlapping_all:
            ret_activities: list[list[SymbolicVariableActivity]] = []
            current = overlapping_all[0]
            for i in range(1, len(overlapping_all)):
                if not self._is_equal(current, overlapping_all[i]):
                    ret_activities.append(current)
                    current = overlapping_all[i]
            ret_activities.append(current)

            for act_vec in ret_activities:
                tmp = ConstraintNetwork(None)
                for act in act_vec:
                    tmp.add_variable(act)
                ret.append(tmp)
            return ret
        return ret

    def _is_equal(
        self, current: list[SymbolicVariableActivity], next_: list[SymbolicVariableActivity]
    ) -> bool:
        if len(current) != len(next_):
            return False
        return sorted(a.id for a in current) == sorted(a.id for a in next_)

    def _complete_peak_collection(
        self, a_to_sf: dict[SymbolicVariableActivity, SpatialFluent]
    ) -> list[ConstraintNetwork]:
        activities = list(a_to_sf.keys())
        if not activities:
            return []

        self.logger.debug("Doing complete peak collection with %d activities...", len(activities))
        discontinuities: list[int] = []
        for act in activities:
            start, end = act.temporal_variable.est, act.temporal_variable.eet
            if start not in discontinuities:
                discontinuities.append(start)
            if end not in discontinuities:
                discontinuities.append(end)
        discontinuities.sort()

        super_peaks: list[list[SymbolicVariableActivity]] = []
        for i in range(len(discontinuities) - 1):
            interval = Bounds(discontinuities[i], discontinuities[i + 1])
            one_peak: list[SymbolicVariableActivity] = []
            for act in activities:
                interval1 = Bounds(act.temporal_variable.est, act.temporal_variable.eet)
                intersection = interval.intersect_strict(interval1)
                if intersection is not None and not intersection.is_singleton:
                    one_peak.append(act)
            super_peaks.append(one_peak)

        ret: list[ConstraintNetwork] = []
        for super_set in super_peaks:
            for s in PowerSet.power_set(super_set):
                if s:
                    cn = ConstraintNetwork(None)
                    for act in s:
                        cn.add_variable(act)
                    if cn not in ret and self.is_conflicting(s, a_to_sf):
                        ret.append(cn)

        self.logger.debug("Done peak sampling")
        return ret

    # --- MetaConstraint interface ------------------------------------------

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        activity_to_fluent: dict[SymbolicVariableActivity, SpatialFluent] = {}
        spatial_fluent_solver = cast(SpatialFluentSolver, self.meta_cs.constraint_solvers[0])  # type: ignore[union-attr]
        for var in spatial_fluent_solver.get_variables():
            fluent = cast(SpatialFluent, var)
            activity_to_fluent[fluent.activity] = fluent
        return self._sampling_peak_collection(activity_to_fluent)
        # return self._complete_peak_collection(activity_to_fluent)

    def get_meta_values(self, meta_variable: MetaVariable | None) -> list[ConstraintNetwork] | None:
        if meta_variable is None:
            return None

        activity_to_fluent: dict[SymbolicVariableActivity, SpatialFluent] = {}
        activities: list[SymbolicVariableActivity] = []
        meta_var_ids: list[int] = []
        spatial_fluent_solver = cast(SpatialFluentSolver, self.meta_cs.constraint_solvers[0])  # type: ignore[union-attr]
        for var in spatial_fluent_solver.get_variables():
            fluent = cast(SpatialFluent, var)
            activities.append(fluent.activity)
            activity_to_fluent[fluent.activity] = fluent
            meta_var_ids.append(fluent.activity.id)
        self._conflict_tracking.append(meta_var_ids)

        self._potential_culprit = []
        ret: list[ConstraintNetwork] = []
        mvalue = ConstraintNetwork(self.meta_cs.constraint_solvers[0])  # type: ignore[union-attr]
        conflict = meta_variable.constraint_network
        assert conflict is not None
        conflictvars: list[SpatialFluent] = []
        conflictrecvars: list[RectangularRegion] = []
        get_variable_by_name: dict[str, RectangularRegion] = {}
        self._old_rectangular_region = {}

        for v in conflict.get_variables():
            fluent = activity_to_fluent[cast("SymbolicVariableActivity", v)]
            conflictvars.append(fluent)
            conflictrecvars.append(fluent.rectangular_region)

        self._set_permutation_hashmap(conflictvars, conflictrecvars)
        alternative_sets = self.generate_all_alternative_set(conflictrecvars)
        alternative_set = alternative_sets[0]

        rectangle_solver = cast(
            RectangleConstraintSolver, spatial_fluent_solver.constraint_solvers[0]
        )
        mvalue.join(self._create_tbox_spatial_network(rectangle_solver, get_variable_by_name))

        meta_variables: list[RectangularRegion] = []
        for var in conflictvars:
            at = alternative_set.get(var.rectangular_region.name)
            if at is None:
                continue
            at_bounds = tuple(Bounds(b.min, b.max) for b in at)
            at_con = UnaryRectangleConstraint(_AT, *at_bounds)
            at_con.from_ = var.rectangular_region
            at_con.to = var.rectangular_region
            meta_variables.append(var.rectangular_region)
            mvalue.add_constraint(at_con)
            mvalue.add_variable(var.rectangular_region)

        new_goal: list[str] = []
        culprit_activities: dict[str, SymbolicVariableActivity] = {}

        for con in list(mvalue.get_constraints()):
            if isinstance(con, UnaryRectangleConstraint) and con.type is _AT:
                b = con.bounds
                if self._is_unbounded_bounding_box(b[0], b[1], b[2], b[3]):
                    region_name = cast(RectangularRegion, con.scope[0]).name
                    for v in conflict.get_variables():
                        act = cast("SymbolicVariableActivity", v)
                        if region_name == activity_to_fluent[act].name:
                            if region_name in self._potential_culprit:
                                if act.temporal_variable.est == act.temporal_variable.lst:
                                    self.logger.debug("%s", region_name)
                                    culprit_activities[region_name] = act
                                    if region_name not in new_goal:
                                        new_goal.append(region_name)

        # Extract the fluent(s) relevant to the original goal(s), e.g. cup1
        # in the "well-set table" scenario.
        original_goals = [
            act
            for act in activity_to_fluent
            if activity_to_fluent[act].name in self._initial_unbounded_obj_name
        ]

        # Maintain the current At unary constraint, for the retraction case.
        self._current_assertional_cons = {}
        for rel in self._s_assertional_rels:
            at_con2 = rel.unary_at_rectangle_constraint
            b2 = at_con2.bounds
            self._current_assertional_cons[rel.from_] = _at_constraint((b2[0], b2[1], b2[2], b2[3]))
            self._old_rectangular_region[rel.from_] = BoundingBox(b2[0], b2[1], b2[2], b2[3])

        new_goal_fluents: list[SpatialFluent] = []
        activity_solver = spatial_fluent_solver.constraint_solvers[1]
        act_network = ConstraintNetwork(activity_solver)

        self._number_of_misplaced = len(new_goal)

        # Set the new goal after the old activity.
        for st in new_goal:
            culprit_act = culprit_activities[st]
            new_goal_fluent = cast(
                SpatialFluent, spatial_fluent_solver.create_variable(culprit_act.component)
            )
            new_goal_fluent.name = st
            new_goal_fluent.activity.set_symbolic_domain(culprit_act.symbolic_variable.symbols[0])
            new_goal_fluent.activity.marking = SimpleDomain.markings.UNJUSTIFIED
            new_goal_fluent.rectangular_region.name = st
            mvalue.add_variable(new_goal_fluent)
            activity_to_fluent[new_goal_fluent.activity] = new_goal_fluent

            new_goal_fluents.append(new_goal_fluent)

            for rel in self._s_assertional_rels:
                if rel.from_ == st:
                    rel.unary_at_rectangle_constraint = UnaryRectangleConstraint(
                        _AT,
                        Bounds(0, APSPSolver.INF),
                        Bounds(0, APSPSolver.INF),
                        Bounds(0, APSPSolver.INF),
                        Bounds(0, APSPSolver.INF),
                    )

            if new_goal_fluent.activity not in activities:
                activities.append(new_goal_fluent.activity)

            new_on_after_old_on = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.After,
                *AllenIntervalConstraint.Type.After.get_default_bounds(),
            )
            new_on_after_old_on.from_ = new_goal_fluent.activity
            new_on_after_old_on.to = culprit_act
            act_network.add_constraint(new_on_after_old_on)

        for rel in self._s_assertional_rels:
            is_added = False
            if rel.from_ in new_goal:
                for ngf in new_goal_fluents:
                    if rel.from_ == ngf.name:
                        target = get_variable_by_name.get(rel.to)
                        if target is not None:
                            assertion = _equals_constraint()
                            assertion.from_ = ngf.rectangular_region
                            assertion.to = target
                            mvalue.add_constraint(assertion)
                is_added = True
            else:
                for mv in meta_variables:
                    if rel.from_ == mv.name:
                        target = get_variable_by_name.get(rel.to)
                        if target is not None:
                            assertion = _equals_constraint()
                            assertion.from_ = mv
                            assertion.to = target
                            mvalue.add_constraint(assertion)
                            is_added = True
            if not is_added:
                for og in original_goals:
                    if activity_to_fluent[og].rectangular_region.name == rel.from_:
                        target = get_variable_by_name.get(rel.to)
                        if target is not None:
                            assertion = _equals_constraint()
                            assertion.from_ = activity_to_fluent[og].rectangular_region
                            assertion.to = target
                            mvalue.add_constraint(assertion)

        act_network.join(mvalue)
        ret.append(act_network)
        act_network.specialized_annotation = self._number_of_misplaced

        return ret

    def temporal_overlap(self, a1: SymbolicVariableActivity, a2: SymbolicVariableActivity) -> bool:
        return not (
            a1.temporal_variable.eet <= a2.temporal_variable.est
            or a2.temporal_variable.eet <= a1.temporal_variable.est
        )

    def mark_resolved_sub(self, meta_variable: MetaVariable, meta_value: ConstraintNetwork) -> None:
        pass

    def is_conflicting(
        self,
        peak: list[SymbolicVariableActivity],
        a_to_sf: dict[SymbolicVariableActivity, SpatialFluent],
    ) -> bool:
        if len(peak) == 1:
            return False

        current_fluent: dict[str, SpatialFluent] = {}
        for act in peak:
            current_fluent[a_to_sf[act].name] = a_to_sf[act]

        iter_solver = RectangleConstraintSolver(self.origin, self.horizon)
        get_variable_by_name: dict[str, RectangularRegion] = {}
        added_general_kn = self._general_knowledge_constraints(iter_solver, get_variable_by_name)
        if not iter_solver.add_constraints(*added_general_kn):
            self.logger.debug("Failed to general knowledge add")

        meta_variables: list[RectangularRegion] = []
        for rel in self._s_assertional_rels:
            sf = current_fluent.get(rel.from_)
            if sf is None:
                continue
            if rel.unary_at_rectangle_constraint is not None:
                var = cast(RectangularRegion, iter_solver.create_variable())
                var.name = rel.from_
                b = rel.unary_at_rectangle_constraint.bounds
                at_con = _at_constraint((b[0], b[1], b[2], b[3]))
                at_con.from_ = var
                at_con.to = var
                meta_variables.append(var)
                if not iter_solver.add_constraint(at_con):
                    self.logger.debug("Failed to add AT constraint")

            if rel.ontological_prop is not None:
                sf.rectangular_region.ontological_prop = rel.ontological_prop

        assertion_list: list[RectangleConstraint] = []
        for rel in self._s_assertional_rels:
            for mv in meta_variables:
                if rel.from_ == mv.name:
                    target = get_variable_by_name.get(rel.to)
                    if target is not None:
                        assertion = _equals_constraint()
                        assertion.from_ = mv
                        assertion.to = target
                        assertion_list.append(assertion)

        is_consistent = True
        if not iter_solver.add_constraints(*assertion_list):
            is_consistent = False

        return not is_consistent

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def __str__(self) -> str:
        return "MetaSpatialAdherenceConstraint "

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> MetaSpatialAdherenceConstraint | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def generate_all_alternative_set(
        self, target_recs: list[RectangularRegion]
    ) -> list[dict[str, list[Bounds]]]:
        level_tracker: dict[int, bool] = {level: False for _, level in self._permutation}
        # (level, rigidity_avg, iter_cn), recorded in generation order for
        # each consistent alternative.
        recorded: list[tuple[int, float, dict[str, list[Bounds]]]] = []

        for iter_cn, level in self._permutation:
            # Incremental generation break: once a lower culprit level has a
            # consistent solution, stop generating higher-level ones.
            if level > 0 and level_tracker.get(level - 1) is True:
                break

            iter_solver = RectangleConstraintSolver(self.origin, self.horizon)
            get_variable_by_name: dict[str, RectangularRegion] = {}
            added_general_kn = self._general_knowledge_constraints(
                iter_solver, get_variable_by_name
            )
            if not iter_solver.add_constraints(*added_general_kn):
                self.logger.debug("Failed to add general knowledge")

            meta_variables: list[RectangularRegion] = []
            for metavar in target_recs:
                if metavar.name not in iter_cn:
                    continue
                var = cast(RectangularRegion, iter_solver.create_variable())
                var.name = metavar.name
                at_bounds = tuple(Bounds(b.min, b.max) for b in iter_cn[metavar.name])
                at_con = UnaryRectangleConstraint(_AT, *at_bounds)
                at_con.from_ = var
                at_con.to = var
                meta_variables.append(var)
                if not iter_solver.add_constraint(at_con):
                    self.logger.debug("Failed to add AT constraint")

            assertion_list: list[RectangleConstraint] = []
            for rel in self._s_assertional_rels:
                for mv in meta_variables:
                    if rel.from_ == mv.name:
                        target = get_variable_by_name.get(rel.to)
                        if target is not None:
                            assertion = _equals_constraint()
                            assertion.from_ = mv
                            assertion.to = target
                            assertion_list.append(assertion)

            is_consistent = True
            if not iter_solver.add_constraints(*assertion_list):
                is_consistent = False
                self.logger.debug(
                    "Failed to add Assertional Constraint in first generation of all "
                    "culprit..alternatives generate later..."
                )

            x_solver = cast(AllenIntervalNetworkSolver, iter_solver.constraint_solvers[0])
            y_solver = cast(AllenIntervalNetworkSolver, iter_solver.constraint_solvers[1])
            rigidity_avg = (x_solver.rigidity_number + y_solver.rigidity_number) / 2

            if is_consistent:
                recorded.append((level, rigidity_avg, iter_cn))
                level_tracker[level] = True

        recorded.sort(key=lambda entry: (entry[0], entry[1]))
        return [iter_cn for _level, _rigidity, iter_cn in recorded]

    def _generate_combination(self, at_constraints: list[UnaryRectangleConstraint]) -> None:
        bounded_unary_cons: list[UnaryRectangleConstraint] = []
        unbounded_unary_cons: list[UnaryRectangleConstraint] = []

        for con in at_constraints:
            internal = con.internal_constraints
            assert internal is not None
            bounds_x = cast(AllenIntervalConstraint, internal[0]).bounds
            bounds_y = cast(AllenIntervalConstraint, internal[1]).bounds
            from_region = cast(RectangularRegion, con.from_)
            if (
                not self._is_unbounded_bounding_box(
                    bounds_x[0], bounds_x[1], bounds_y[0], bounds_y[1]
                )
                and from_region.ontological_prop.is_movable
            ):
                self._potential_culprit.append(from_region.name)
                self.logger.debug("one potential culprit can be: %s", from_region.name)
                bounded_unary_cons.append(con)
            else:
                unbounded_unary_cons.append(con)

        rank: list[tuple[list[UnaryRectangleConstraint], int]] = []
        gen = PermutationsWithRepetition(2, len(bounded_unary_cons))
        for variation in gen.get_variations():
            tmp_bounded_unary_cons: list[UnaryRectangleConstraint] = []
            culprit_number = 0
            for j, vij in enumerate(variation):
                if vij == 1:
                    utmp = UnaryRectangleConstraint(
                        _AT,
                        Bounds(0, APSPSolver.INF),
                        Bounds(0, APSPSolver.INF),
                        Bounds(0, APSPSolver.INF),
                        Bounds(0, APSPSolver.INF),
                    )
                    utmp.from_ = bounded_unary_cons[j].from_
                    utmp.to = bounded_unary_cons[j].to
                    tmp_bounded_unary_cons.append(utmp)
                    culprit_number += 1
                else:
                    tmp_bounded_unary_cons.append(bounded_unary_cons[j])
            rank.append((tmp_bounded_unary_cons, culprit_number))

        permutation: list[tuple[dict[str, list[Bounds]], int]] = []
        for cc, level in rank:
            culprit: dict[str, list[Bounds]] = {}
            for con in cc:
                culprit[cast(RectangularRegion, con.from_).name] = _four_bounds(con)
            for con in unbounded_unary_cons:
                culprit[cast(RectangularRegion, con.from_).name] = _four_bounds(con)
            permutation.append((culprit, level))

        self._permutation = sorted(permutation, key=lambda kv: kv[1])

    def _is_unbounded_bounding_box(
        self, x_lb: Bounds | None, x_ub: Bounds | None, y_lb: Bounds | None, y_ub: Bounds | None
    ) -> bool:
        assert x_lb is not None and x_ub is not None and y_lb is not None and y_ub is not None
        if x_lb.min != 0 and x_lb.max != APSPSolver.INF:
            return False
        if x_ub.min != 0 and x_ub.max != APSPSolver.INF:
            return False
        if y_lb.min != 0 and y_lb.max != APSPSolver.INF:
            return False
        # Ported verbatim, including the upstream bug: this last conjunct
        # re-checks ``y_lb.min`` instead of ``y_ub.min`` (see the identical
        # note in rectangular_region.py's ``is_unbounded``).
        if y_lb.min != 0 and y_ub.max != APSPSolver.INF:
            return False
        return True

    def _set_permutation_hashmap(
        self, conflictvars: list[SpatialFluent], target_recs: list[RectangularRegion]
    ) -> None:
        at_constraints: list[UnaryRectangleConstraint] = []
        current_fluent: dict[str, SpatialFluent] = {sf.name: sf for sf in conflictvars}

        iter_solver = RectangleConstraintSolver(self.origin, self.horizon)
        for rel in self._s_assertional_rels:
            sf = current_fluent.get(rel.from_)
            if sf is None:
                continue
            var = cast(RectangularRegion, iter_solver.create_variable())
            if rel.unary_at_rectangle_constraint is not None:
                var.name = rel.from_
                b = rel.unary_at_rectangle_constraint.bounds
                at_con = _at_constraint((b[0], b[1], b[2], b[3]))
                at_con.from_ = var
                at_con.to = var
                at_constraints.append(at_con)
                if not iter_solver.add_constraint(at_con):
                    self.logger.debug("Failed to add AT constraint")

            if rel.ontological_prop is not None:
                var.ontological_prop = rel.ontological_prop

        self._generate_combination(at_constraints)

    def get_ground_solver(self) -> ConstraintSolver:
        # Java's implementation is an unfinished stub (``return null;``) --
        # reproduced verbatim; this class's ground solver is never actually
        # obtained through this method by the rest of the package (compare
        # MetaOccupiedConstraint.getGroundSolver, which is fully implemented).
        return None  # type: ignore[return-value]


def _four_bounds(con: UnaryRectangleConstraint) -> list[Bounds]:
    internal = con.internal_constraints
    assert internal is not None
    x = cast(AllenIntervalConstraint, internal[0]).bounds
    y = cast(AllenIntervalConstraint, internal[1]).bounds
    assert x[0] is not None and x[1] is not None and y[0] is not None and y[1] is not None
    return [x[0], x[1], y[0], y[1]]
