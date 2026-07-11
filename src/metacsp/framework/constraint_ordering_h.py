"""Port of framework/ConstraintOrderingH.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["ConstraintOrderingH"]


class ConstraintOrderingH(ABC):
    """Abstract class for constraint ordering heuristics (Comparator<Constraint>)
    used in backtracking search (e.g., MetaConstraintSolver)."""

    @abstractmethod
    def collect_data(self, all_meta_constraints: Sequence[Constraint]) -> None: ...

    @abstractmethod
    def compare(self, c1: Constraint, c2: Constraint) -> int:
        """Negative if c1 sorts before c2, zero if equivalent, positive otherwise."""
