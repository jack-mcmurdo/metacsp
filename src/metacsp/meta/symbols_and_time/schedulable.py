"""Port of meta/symbolsAndTime/Schedulable.java."""

from __future__ import annotations

import functools
from abc import abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.multi.activity.activity import Activity
from metacsp.multi.activity.activity_comparator import ActivityComparator
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.meta.symbols_and_time.mcs_data import MCSData
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.utility.math import PowerSet

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH

__all__ = ["Schedulable"]


class Schedulable(MetaConstraint):
    """Common base for MetaConstraints that arbitrate access to a shared
    resource by sequencing overlapping Activities ("peaks") that conflict.

    Subclasses define what makes a set of overlapping Activities conflicting
    (:meth:`is_conflicting`); this class collects such peaks
    (:meth:`get_meta_variables`, three strategies) and, for a given peak,
    proposes precedence constraints resolving it in decreasing order of
    estimated remaining flexibility (:meth:`get_meta_values`, the ESTA
    heuristic -- see :class:`~metacsp.meta.symbols_and_time.mcs_data.MCSData`).
    """

    class PEAKCOLLECTION(Enum):
        SAMPLING = auto()
        COMPLETE = auto()
        BINARY = auto()

    def __init__(self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None) -> None:
        super().__init__(var_oh, val_oh)
        self.before_parameter: int = 0
        self.activities: list[Activity] | None = None
        self.peak_collection_strategy: Schedulable.PEAKCOLLECTION = (
            Schedulable.PEAKCOLLECTION.SAMPLING
        )

    # --- peak collection strategies ---

    def _sampling_peak_collection(self) -> list[ConstraintNetwork]:
        """Find sets of overlapping activities and assess whether they are
        conflicting (e.g. over-consuming a resource)."""
        if not self.activities:
            return []

        ground_vars = sorted(
            self.activities,
            key=functools.cmp_to_key(ActivityComparator(True).compare),
        )

        ret: list[ConstraintNetwork] = []
        usages: dict[Activity, ConstraintNetwork] = {}
        overlapping_all: list[list[Activity]] = []

        # First check whether a single activity is over-consuming the resource.
        for act in self.activities:
            if self.is_conflicting([act]):
                temp = ConstraintNetwork(None)
                temp.add_variable(act.variable)
                ret.append(temp)

        # ground_vars are ordered activities.
        for i in range(len(ground_vars)):
            overlapping = [ground_vars[i]]
            start = ground_vars[i].temporal_variable.est
            end = ground_vars[i].temporal_variable.eet
            intersection: Bounds | None = Bounds(start, end)
            # Starting from ground_vars[i], all forthcoming activities are
            # evaluated to see if they temporally overlap with ground_vars[i].
            for j in range(len(ground_vars)):
                if i == j:
                    continue
                start = ground_vars[j].temporal_variable.est
                end = ground_vars[j].temporal_variable.eet
                next_interval = Bounds(start, end)
                assert intersection is not None
                intersection_new = intersection.intersect_strict(next_interval)
                if intersection_new is not None:
                    overlapping.append(ground_vars[j])
                    if self.is_conflicting(overlapping):
                        overlapping_all.append(overlapping)
                        break
                    intersection = intersection_new

        for overlapping in overlapping_all:
            if len(overlapping) > 1:
                first = overlapping[0]
                temp = ConstraintNetwork(None)
                for act in overlapping:
                    temp.add_variable(act.variable)
                usages[first] = temp

        for cn in usages.values():
            if len(cn.get_variables()) > 1:
                ret.append(cn)

        return ret

    def _complete_peak_collection(self) -> list[ConstraintNetwork]:
        if not self.activities:
            return []
        self.logger.debug(
            "Doing complete peak collection with %d activities...", len(self.activities)
        )
        ground_vars = list(self.activities)
        discontinuities: list[int] = []
        for a in ground_vars:
            start = a.temporal_variable.est
            end = a.temporal_variable.eet
            if start not in discontinuities:
                discontinuities.append(start)
            if end not in discontinuities:
                discontinuities.append(end)
        discontinuities.sort()

        super_peaks: list[list[Activity]] = []
        seen_peaks: set[frozenset[int]] = set()
        for i in range(len(discontinuities) - 1):
            one_peak: list[Activity] = []
            interval = Bounds(discontinuities[i], discontinuities[i + 1])
            for a in ground_vars:
                interval1 = Bounds(a.temporal_variable.est, a.temporal_variable.eet)
                intersection = interval.intersect_strict(interval1)
                if intersection is not None and not intersection.is_singleton:
                    if a not in one_peak:
                        one_peak.append(a)
            # HashSet<HashSet<Activity>> in Java dedupes identical peaks.
            key = frozenset(id(a) for a in one_peak)
            if key not in seen_peaks:
                seen_peaks.add(key)
                super_peaks.append(one_peak)

        ret: list[ConstraintNetwork] = []
        for super_set in super_peaks:
            for s in PowerSet.power_set(super_set):
                if s:
                    cn = ConstraintNetwork(None)
                    for a in s:
                        cn.add_variable(a.variable)
                    # Java's `!ret.contains(cn)` never filters (ConstraintNetwork
                    # compares by identity and cn is always a fresh instance);
                    # reproduced as-is by not de-duplicating here either.
                    if self.is_conflicting(s):
                        ret.append(cn)
        self.logger.debug("Done peak sampling")
        return ret

    def _binary_peak_collection(self) -> list[ConstraintNetwork]:
        if not self.activities:
            return []
        ret: list[ConstraintNetwork] = []
        self.logger.debug(
            "Doing binary peak collection with %d activities...", len(self.activities)
        )
        ground_vars = list(self.activities)
        for a in ground_vars:
            if self.is_conflicting([a]):
                cn = ConstraintNetwork(None)
                cn.add_variable(a.variable)
                ret.append(cn)
        if ret:
            return ret
        for i in range(len(ground_vars) - 1):
            for j in range(i + 1, len(ground_vars)):
                bi = Bounds(
                    ground_vars[i].temporal_variable.est, ground_vars[i].temporal_variable.eet
                )
                bj = Bounds(
                    ground_vars[j].temporal_variable.est, ground_vars[j].temporal_variable.eet
                )
                if bi.intersect_strict(bj) is not None and self.is_conflicting(
                    [ground_vars[i], ground_vars[j]]
                ):
                    cn = ConstraintNetwork(None)
                    cn.add_variable(ground_vars[i].variable)
                    cn.add_variable(ground_vars[j].variable)
                    ret.append(cn)
        return ret

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        if self.peak_collection_strategy is Schedulable.PEAKCOLLECTION.SAMPLING:
            return self._sampling_peak_collection()
        if self.peak_collection_strategy is Schedulable.PEAKCOLLECTION.BINARY:
            return self._binary_peak_collection()
        return self._complete_peak_collection()

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork] | None:
        conflict = meta_variable.constraint_network
        assert conflict is not None
        mcs_info = self.get_ordered_mcss(conflict)

        if mcs_info is None:  # Unresolvable MCS: no solution can be found.
            return None

        ret: list[ConstraintNetwork] = []
        for mcs in mcs_info:
            before = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.BeforeOrMeets,
                Bounds(self.before_parameter, APSPSolver.INF),
            )
            before.from_ = mcs.mcs_act_from.variable
            before.to = mcs.mcs_act_to.variable
            resolver = ConstraintNetwork(mcs.mcs_act_from.variable.constraint_solver)
            resolver.add_variable(mcs.mcs_act_from.variable)
            resolver.add_variable(mcs.mcs_act_to.variable)
            resolver.add_constraint(before)
            ret.append(resolver)

        return ret

    def get_ordered_mcss(self, peak: ConstraintNetwork) -> list[MCSData] | None:
        """Get MCSs of the given peak, ordered by decreasing k, a heuristic
        estimator of the flexibility maintained when imposing a temporal
        constraint that resolves an MCS -- see [P. Laborie, M. Ghallab,
        "Planning with Sharable Resource Constraints", IJCAI 1995]."""
        mcslist: list[tuple[Activity, Activity]] = []
        vars_ = peak.get_variables()
        for i in range(len(vars_)):
            for j in range(i + 1, len(vars_)):
                mcslist.append((cast(Activity, vars_[i]), cast(Activity, vars_[j])))

        mcsinfo: list[MCSData] = []
        index = 0
        unres_mcs_found = False

        while not unres_mcs_found and index < len(mcslist):
            pcmin = 1.0
            pcmin_bad = 1.0
            k_reciprocal = 0.0
            act_from: Activity | None = None
            act_to: Activity | None = None
            unres_mcs = 0

            current_mcs = mcslist[index]
            pc_vector: list[float] = []
            mcs_size = len(current_mcs)

            for g in range(mcs_size):
                est1 = current_mcs[g].temporal_variable.est
                # Java bug reproduced verbatim: eet1 is assigned getEST(),
                # not getEET(), and is used (as-is) below in the dmax
                # computation for the direct pair -- this affects the
                # computed pcmin/ordering, so it is observable behavior, not
                # mere dead code.
                eet1 = current_mcs[g].temporal_variable.est
                lst1 = current_mcs[g].temporal_variable.lst
                let1 = current_mcs[g].temporal_variable.let

                for h in range(g + 1, mcs_size):
                    est2 = current_mcs[h].temporal_variable.est
                    eet2 = current_mcs[h].temporal_variable.eet
                    lst2 = current_mcs[h].temporal_variable.lst
                    let2 = current_mcs[h].temporal_variable.let

                    # Direct pair.
                    dmin = est2 - let1
                    dmax = lst2 - eet1
                    if dmin > dmax:
                        raise RuntimeError("Direct pair and dmin > dmax: IMPOSSIBLE")

                    pc = 0.0
                    if dmin != dmax:
                        pc = (min(dmax, 0) - min(dmin, 0)) / (dmax - dmin)
                        pc_vector.append(pc)
                        if pc < pcmin:
                            pcmin = pc
                            pcmin_bad = pcmin
                            act_from = current_mcs[g]
                            act_to = current_mcs[h]
                        else:
                            unres_mcs += 1
                    else:
                        unres_mcs += 1

                    # Inverse pair.
                    dmin = est1 - let2
                    dmax = lst1 - eet2
                    if dmin > dmax:
                        raise RuntimeError("Inverse pair and dmin > dmax: IMPOSSIBLE")

                    if dmin != dmax:
                        pc = (min(dmax, 0) - min(dmin, 0)) / (dmax - dmin)
                        pc_vector.append(pc)
                        if pc < pcmin:
                            pcmin = pc
                            act_from = current_mcs[h]
                            act_to = current_mcs[g]
                        else:
                            unres_mcs += 1
                    else:
                        unres_mcs += 1

            if unres_mcs < mcs_size * (mcs_size - 1):
                for pc in pc_vector:
                    k_reciprocal += 1.0 / (1.0 + pc - pcmin)
                assert act_from is not None and act_to is not None
                k = 1.0 if k_reciprocal == 0.0 else 1.0 / k_reciprocal
                mcsinfo.append(MCSData(pcmin, act_from, act_to, k))
                mcsinfo.append(MCSData(pcmin_bad, act_to, act_from, k))
                index += 1
            else:
                unres_mcs_found = True

        if unres_mcs_found:
            return None
        return sorted(mcsinfo)

    def _temporal_overlap(self, a1: Activity, a2: Activity) -> bool:
        return not (
            a1.temporal_variable.eet <= a2.temporal_variable.est
            or a2.temporal_variable.eet <= a1.temporal_variable.est
        )

    def mark_resolved_sub(self, con: MetaVariable, meta_value: ConstraintNetwork) -> None:
        pass

    @abstractmethod
    def is_conflicting(self, peak: list[Activity]) -> bool:
        """True iff the given set of overlapping Activities conflicts (e.g.
        overuses a shared resource)."""

    def set_usage(self, *acts: Activity) -> None:
        if self.activities is None:
            self.activities = []
        for act in acts:
            if act not in self.activities:
                self.activities.append(act)

    def remove_usage(self, *acts: Activity) -> None:
        if self.activities is not None:
            for act in acts:
                if act in self.activities:
                    self.activities.remove(act)

    @property
    def activity_on_use(self) -> list[Activity] | None:
        return self.activities
