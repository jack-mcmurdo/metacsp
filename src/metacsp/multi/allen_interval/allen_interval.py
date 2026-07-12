"""Port of multi/allenInterval/AllenInterval.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.domain import Domain
from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.time.bounds import Bounds
from metacsp.time.time_point import TimePoint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable
    from metacsp.time.apsp_solver import APSPSolver

__all__ = ["AllenInterval"]


class AllenInterval(MultiVariable):
    """A MultiVariable representing an Allen interval as two TimePoints (its
    start and end), used for quantitative temporal reasoning."""

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id, internal_solvers, internal_vars)
        self.name = ""

    def is_intersecting_earliest_start_time(self, i: AllenInterval) -> bool:
        """True iff this interval's [EST,EET] intersects the given
        interval's [EST,EET]."""
        this_bounds = Bounds(self.est, self.eet)
        that_bounds = Bounds(i.est, i.eet)
        return this_bounds.is_intersecting(that_bounds)

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        """Post the default Duration constraint between this interval's own start and end."""
        from metacsp.multi.allen_interval.allen_interval_constraint import (
            AllenIntervalConstraint,
        )

        dur = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Duration,
            *AllenIntervalConstraint.Type.Duration.get_default_bounds(),
        )
        dur.from_ = self
        dur.to = self
        dur.auto_removable = True
        s = cast("APSPSolver", self.constraint_solver.constraint_solvers[0])  # type: ignore[attr-defined]
        s.set_adding_independent_constraints()
        return [dur]

    @property
    def domain(self) -> Domain:
        """This interval's domain, as a MultiDomain over its start/end TimePoints."""
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        """No-op: an AllenInterval's domain is derived from its start/end TimePoints."""
        pass

    @property
    def start(self) -> TimePoint:
        """This interval's start TimePoint."""
        return cast(TimePoint, self.variables[0])

    @start.setter
    def start(self, s: TimePoint) -> None:
        """Set this interval's start TimePoint."""
        self.variables[0] = s

    @property
    def end(self) -> TimePoint:
        """This interval's end TimePoint."""
        return cast(TimePoint, self.variables[1])

    @end.setter
    def end(self, e: TimePoint) -> None:
        """Set this interval's end TimePoint."""
        self.variables[1] = e

    @property
    def est(self) -> int:
        """Earliest start time."""
        return self.start.domain.choose_value("ET")

    @property
    def lst(self) -> int:
        """Latest start time."""
        return self.start.domain.choose_value("LT")

    @property
    def eet(self) -> int:
        """Earliest end time."""
        return self.end.domain.choose_value("ET")

    @property
    def let(self) -> int:
        """Latest end time."""
        return self.end.domain.choose_value("LT")

    @property
    def duration(self) -> Bounds:
        """The [min, max] duration bounds implied by this interval's start/end bounds."""
        min_dur = self.end.domain.choose_value("ET") - self.start.domain.choose_value("LT")
        max_dur = self.end.domain.choose_value("LT") - self.start.domain.choose_value("ET")
        return Bounds(min_dur, max_dur)

    def __str__(self) -> str:
        if self.name == "":
            vars_str = " ".join(str(v) for v in self.variables)
            return f"{type(self).__name__} {self.id}<{vars_str}> {self.domain}"
        return f"{self.name} {self.id} {self.domain}"

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id
