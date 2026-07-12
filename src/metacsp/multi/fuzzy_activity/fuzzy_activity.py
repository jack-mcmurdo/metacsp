"""Port of multi/fuzzyActivity/FuzzyActivity.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.fuzzy_symbols.fuzzy_symbolic_variable import FuzzySymbolicVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable

__all__ = ["FuzzyActivity"]


class FuzzyActivity(MultiVariable):
    """A MultiVariable pairing a (crisp) SimpleAllenInterval temporal
    placement with a FuzzySymbolicVariable value."""

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id, internal_solvers, internal_vars)
        self.dependencies: list[FuzzyActivity] = []
        self.is_hypothesis = False

    def set_domain(self, symbols: list[str], vals: list[float]) -> None:
        cast(FuzzySymbolicVariable, self.internal_variables[1]).set_domain(symbols, vals)

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        return None

    @property
    def domain(self) -> Any:
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        pass

    def __str__(self) -> str:
        return f"<{self.internal_variables[1]}>U<{self.internal_variables[0]}>"

    def __lt__(self, other: Variable) -> bool:
        return False
