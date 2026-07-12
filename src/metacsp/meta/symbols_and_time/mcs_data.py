"""Port of meta/symbolsAndTime/MCSData.java."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.multi.activity.activity import Activity

__all__ = ["MCSData"]


@functools.total_ordering
class MCSData:
    """Data structure holding the information associated to a minimal
    critical set (MCS): a set of Activity variables such that imposing only
    one precedence constraint among any two of them resolves an n-ary
    conflict (e.g. a resource conflict).

    The ESTA scheduling algorithm infers MCSs and attempts to impose
    constraints that sequence one Activity in the MCS with respect to the
    others; the heuristic chooses to post constraints such that (1)
    sequencing the two decisions (i,j) involved in each constraint has
    "minimal" consequences with respect to the temporal flexibility
    (FLEX(i,j)) of the underlying temporal network, and (2) the MCS from
    which the decisions are chosen at each iteration has the highest value
    of k, a function of FLEX(i,j) for all pairs of activities (i,j) in the
    MCS. See [A. Cesta, A. Oddi and S. F. Smith, "A Constraint-based Method
    for Project Scheduling with Time Windows", Journal of Heuristics 8(1),
    2002] and [P. Laborie, M. Ghallab, "Planning with Sharable Resource
    Constraints", IJCAI 1995].
    """

    def __init__(self, pcmin: float, act_from: Activity, act_to: Activity, k: float) -> None:
        self.mcs_k = k
        self.mcs_act_from = act_from
        self.mcs_act_to = act_to
        self.mcs_pc_min = pcmin

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MCSData):
            return NotImplemented
        return self.mcs_k == other.mcs_k

    def __lt__(self, other: MCSData) -> bool:
        # Java's compareTo(o) returns -1 (this sorts first) when
        # self.mcs_k > o.mcs_k, so Arrays.sort (ascending by compareTo)
        # yields *decreasing* mcs_k order. Mirror that: self < other means
        # self sorts first, i.e. self.mcs_k > other.mcs_k.
        return self.mcs_k > other.mcs_k

    def __str__(self) -> str:
        return (
            f"[K = {self.mcs_k}, pcMin = {self.mcs_pc_min}, "
            f"ActFrom = {self.mcs_act_from}, ActTo = {self.mcs_act_to}]"
        )
