"""Port of multi/activity/SymbolicVariableActivity.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.multi.activity.activity import Activity
from metacsp.multi.allen_interval.allen_interval import AllenInterval
from metacsp.multi.symbols.symbolic_variable import SymbolicVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable

__all__ = ["SymbolicVariableActivity"]


class SymbolicVariableActivity(MultiVariable, Activity):
    """An Activity: a MultiVariable pairing an AllenInterval (temporal
    placement) with a SymbolicVariable (symbolic value)."""

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id, internal_solvers, internal_vars)

    def set_symbolic_domain(self, *symbols: str) -> None:
        """Restrict this Activity's symbolic value to the given set of symbols."""
        self.symbolic_variable.set_symbolic_domain(*symbols)

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        """No internal constraints: the temporal and symbolic parts are independent."""
        return None

    @property
    def domain(self) -> Any:
        """This Activity's domain, as a MultiDomain over its temporal and symbolic parts."""
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        """No-op: a SymbolicVariableActivity's domain is derived from its internal variables."""
        pass

    def __str__(self) -> str:
        ret = f"{self.component}({self.id})::<{self.internal_variables[1]}>U<{self.internal_variables[0]}>"
        if self.marking is not None:
            ret += f"/{self.marking}"
        return ret

    def __lt__(self, other: Variable) -> bool:
        if isinstance(other, SymbolicVariableActivity):
            return self.temporal_variable.est - other.temporal_variable.est < 0
        return False

    @property
    def symbolic_variable(self) -> SymbolicVariable:
        """This Activity's symbolic-value internal variable."""
        return cast(SymbolicVariable, self.internal_variables[1])

    @property
    def temporal_variable(self) -> AllenInterval:
        """This Activity's temporal-placement internal variable."""
        return cast(AllenInterval, self.internal_variables[0])

    @property
    def variable(self) -> Variable:
        """This Activity's own Variable identity (itself)."""
        return self

    @property
    def symbols(self) -> list[str]:
        """This Activity's current symbolic value(s)."""
        return self.symbolic_variable.symbols
