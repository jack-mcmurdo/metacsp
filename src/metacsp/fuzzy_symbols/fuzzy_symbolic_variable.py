"""Port of fuzzySymbols/FuzzySymbolicVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.domain import Domain
from metacsp.framework.variable import Variable
from metacsp.fuzzy_symbols.fuzzy_symbolic_domain import FuzzySymbolicDomain

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["FuzzySymbolicVariable"]


class FuzzySymbolicVariable(Variable):
    """A variable whose domain is a fuzzy set (see FuzzySymbolicDomain)."""

    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._dom: FuzzySymbolicDomain | None = None
        self._backup_dom: FuzzySymbolicDomain | None = None

    @property
    def domain(self) -> Domain | None:
        return self._dom

    @domain.setter
    def domain(self, d: Domain) -> None:
        if isinstance(d, FuzzySymbolicDomain):
            self._dom = d
            self._backup_dom = cast(FuzzySymbolicDomain, d.clone())

    def set_domain(self, symbols: list[str], possibilities: list[float]) -> None:
        self._dom = FuzzySymbolicDomain(self, symbols, possibilities)
        self._backup_dom = cast(FuzzySymbolicDomain, self._dom.clone())

    def get_symbols_and_possibilities(self) -> dict[str, float]:
        assert self._dom is not None
        return self._dom.get_symbols_and_possibilities()

    def __str__(self) -> str:
        return f"{type(self).__name__} {self.id} {self.domain}"

    def __lt__(self, other: Variable) -> bool:
        return False

    def reset_domain(self) -> None:
        if self._backup_dom is not None:
            self._dom = cast(FuzzySymbolicDomain, self._backup_dom.clone())
