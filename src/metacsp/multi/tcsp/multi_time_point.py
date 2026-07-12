"""Port of multi/TCSP/MultiTimePoint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.time.time_point import TimePoint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable

__all__ = ["MultiTimePoint"]


class MultiTimePoint(MultiVariable):
    """A MultiVariable wrapping a single internal TimePoint, used by
    DistanceConstraintSolver (a TCSP built on top of an APSPSolver)."""

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id, internal_solvers, internal_vars)

    def __lt__(self, other: Variable) -> bool:
        return False

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        return None

    @property
    def domain(self) -> Any:
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        pass

    def __str__(self) -> str:
        return str(self.internal_variables[0])

    def set_time_point(self, tp: TimePoint) -> None:
        self.variables[0] = tp

    @property
    def lower_bound(self) -> int:
        return cast(TimePoint, self.internal_variables[0]).lower_bound

    @property
    def upper_bound(self) -> int:
        return cast(TimePoint, self.internal_variables[0]).upper_bound
