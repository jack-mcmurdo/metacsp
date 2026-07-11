"""Port of time/SimpleDistanceConstraint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.binary_constraint import BinaryConstraint
from metacsp.time.bounds import INF, Bounds, print_long

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["SimpleDistanceConstraint"]


class SimpleDistanceConstraint(BinaryConstraint):
    """The fundamental building block for STPs: the simple distance
    constraint type used by the APSPSolver STP solver."""

    def __init__(self) -> None:
        super().__init__()
        self.minimum: int = 0
        self.maximum: int = 0
        self._bs: list[Bounds] = []

    def __str__(self) -> str:
        return f"{super().__str__()} INTVS: {self._bs}"

    @property
    def counter(self) -> int:
        """Number of [lb,ub] intervals added between the two TimePoints
        (including the active constraint)."""
        return len(self._bs)

    def add_interval(self, i: Bounds) -> bool:
        if i.max < self.minimum or i.min > self.maximum:
            return False
        self._bs.append(i)
        return True

    def remove_interval(self, i: Bounds) -> bool:
        try:
            self._bs.remove(i)
        except ValueError:
            return False
        intersection = Bounds(0, INF)
        for to_intersect in self._bs:
            intersection = intersection.intersect(to_intersect)
        self.minimum = intersection.min
        self.maximum = intersection.max
        return True

    @property
    def edge_label(self) -> str:
        return f"[{print_long(self.minimum)},{print_long(self.maximum)}]"

    def clone(self) -> SimpleDistanceConstraint:
        sdc = SimpleDistanceConstraint()
        sdc.from_ = self.from_
        sdc.to = self.to
        sdc.minimum = self.minimum
        sdc.maximum = self.maximum
        return sdc

    def normalize(self) -> SimpleDistanceConstraint:
        """Invert the constraint if its lower bound is negative (at the time
        of writing, negative bounds could not otherwise be used)."""
        if self.minimum < 0:
            return self.invert()
        return self.clone()

    def invert(self) -> SimpleDistanceConstraint:
        new_constraint = SimpleDistanceConstraint()
        new_constraint.minimum = -self.maximum
        new_constraint.maximum = -self.minimum
        new_constraint.from_ = self.to
        new_constraint.to = self.from_
        return new_constraint

    def is_equivalent(self, c: Constraint) -> bool:
        return c == self
