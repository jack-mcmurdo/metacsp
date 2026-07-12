"""Port of fuzzySymbols/FuzzySymbolicDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.exceptions import PossibilityDegreeMismathcException
from metacsp.framework.domain import Domain

if TYPE_CHECKING:
    from metacsp.fuzzy_symbols.fuzzy_symbolic_variable import FuzzySymbolicVariable

__all__ = ["FuzzySymbolicDomain"]


class FuzzySymbolicDomain(Domain):
    """A fuzzy set: a domain of a FuzzySymbolicVariable, mapping each symbol
    to a possibility degree in [0,1]."""

    def __init__(
        self,
        v: FuzzySymbolicVariable,
        symbols: list[str],
        possibilities: list[float] | None = None,
    ) -> None:
        super().__init__(v)
        self.the_domain: dict[str, float] = {}
        if possibilities is not None:
            if len(possibilities) != len(symbols):
                self.logger.error("%s", PossibilityDegreeMismathcException(self, possibilities))
            for s, p in zip(symbols, possibilities):
                self.the_domain[s] = p
        else:
            for s in symbols:
                self.the_domain[s] = 0.0

    def get_symbols(self) -> list[str]:
        return list(self.the_domain.keys())

    def get_possibility_degrees(self) -> list[float]:
        return list(self.the_domain.values())

    def get_symbols_and_possibilities(self) -> dict[str, float]:
        return self.the_domain

    def __str__(self) -> str:
        return f"{self.get_symbols()} Poss: {self.get_possibility_degrees()}"

    def compare_to(self, o: object) -> int:
        return 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FuzzySymbolicDomain):
            return False
        s_a = self.get_symbols()
        s_b = other.get_symbols()
        p_a = self.get_possibility_degrees()
        p_b = other.get_possibility_degrees()
        if len(s_a) != len(s_b):
            return False
        for i in range(len(s_a)):
            if s_a[i] != s_b[i] or p_a[i] != p_b[i]:
                return False
        return True

    # Java overrides equals() but not hashCode(), inheriting identity hashCode
    # (an inconsistency present in the original); mirror it rather than fix it.
    __hash__ = object.__hash__

    def clone(self) -> FuzzySymbolicDomain:
        return FuzzySymbolicDomain(
            self.variable, self.get_symbols(), self.get_possibility_degrees()
        )
