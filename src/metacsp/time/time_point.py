"""Port of time/TimePoint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain
from metacsp.framework.variable import Variable
from metacsp.time.bounds import print_long
from metacsp.time.interval import Interval

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.time.simple_distance_constraint import SimpleDistanceConstraint

__all__ = ["TimePoint"]


class TimePoint(Variable):
    """The building block of the APSPSolver temporal reasoner.

    As with all Variables, TimePoints should be created through a solver
    factory method (APSPSolver's ``create_variables``), not directly.
    """

    def __init__(
        self,
        id: int,
        max_tps: int,
        sol: ConstraintSolver,
        lb: int = 0,
        ub: int = 0,
    ) -> None:
        super().__init__(sol, id)
        self.out: list[SimpleDistanceConstraint | None] = [None] * max_tps
        self._used = False
        self._lower_bound = lb
        self._upper_bound = ub

    def __str__(self) -> str:
        return f"{self.id}:{{{print_long(self.lower_bound)},{print_long(self.upper_bound)}}}"

    @property
    def lower_bound(self) -> int:
        return self._lower_bound

    @lower_bound.setter
    def lower_bound(self, new_val: int) -> None:
        self._lower_bound = new_val

    @property
    def upper_bound(self) -> int:
        return self._upper_bound

    @upper_bound.setter
    def upper_bound(self, new_val: int) -> None:
        self._upper_bound = new_val

    @property
    def used(self) -> bool:
        """Whether this TimePoint is currently used in the temporal network."""
        return self._used

    @used.setter
    def used(self, new_val: bool) -> None:
        if self._used and not new_val:
            self.out = [None] * len(self.out)
        self._used = new_val

    def get_out(self, i: int) -> SimpleDistanceConstraint | None:
        return self.out[i]

    def set_out(self, i: int, new_val: SimpleDistanceConstraint | None) -> None:
        self.out[i] = new_val

    @property
    def domain(self) -> Domain:
        return Interval(self, self.lower_bound, self.upper_bound)

    @domain.setter
    def domain(self, d: Domain) -> None:
        if isinstance(d, Interval):
            self._lower_bound = d.lower_bound
            self._upper_bound = d.upper_bound

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    def clone(self) -> TimePoint:
        c = TimePoint(self.id, len(self.out), self.constraint_solver)
        c.lower_bound = self.lower_bound
        c.upper_bound = self.upper_bound
        c.used = self.used
        for i, sdc in enumerate(self.out):
            c.out[i] = sdc.clone() if sdc is not None else None
        return c
