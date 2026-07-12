"""Port of multi/TCSP/DistanceConstraint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.multi.multi_binary_constraint import MultiBinaryConstraint
from metacsp.multi.tcsp.multi_time_point import MultiTimePoint
from metacsp.time.simple_distance_constraint import SimpleDistanceConstraint
from metacsp.time.time_point import TimePoint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.time.bounds import Bounds

__all__ = ["DistanceConstraint"]


class DistanceConstraint(MultiBinaryConstraint):
    """A (possibly disjunctive) distance constraint between two
    MultiTimePoints, lifted down to one SimpleDistanceConstraint per
    disjunct in the internal APSPSolver."""

    def __init__(self, *intervals: Bounds) -> None:
        super().__init__()
        self.intervals = list(intervals)
        if len(self.intervals) != 1:
            self.set_propagate_later()
        else:
            self.set_propagate_immediately()

    def create_internal_constraints_from_to(
        self, from_: Variable, to: Variable
    ) -> list[Constraint] | None:
        tp_from = cast(TimePoint, cast(MultiTimePoint, from_).internal_variables[0])
        tp_to = cast(TimePoint, cast(MultiTimePoint, to).internal_variables[0])
        ret: list[SimpleDistanceConstraint] = []
        for interval in self.intervals:
            con = SimpleDistanceConstraint()
            con.from_ = tp_from
            con.to = tp_to
            con.minimum = interval.min
            con.maximum = interval.max
            ret.append(con)
        return ret

    def clone(self) -> DistanceConstraint:
        return DistanceConstraint(*self.intervals)

    @property
    def edge_label(self) -> str:
        return "".join(str(interval) for interval in self.intervals)

    @property
    def bounds(self) -> list[Bounds]:
        return self.intervals

    def is_equivalent(self, c: Constraint) -> bool:
        dc = cast(DistanceConstraint, c)
        if not (dc.from_ == self.from_ and dc.to == self.to):
            return False
        for t in self.bounds:
            found = False
            for t1 in dc.bounds:
                if t == t1:
                    found = True
                    break
                if not found:
                    return False
        return True
