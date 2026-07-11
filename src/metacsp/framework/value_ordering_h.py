"""Port of framework/ValueOrderingH.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork

__all__ = ["ValueOrderingH"]


class ValueOrderingH(ABC):
    """Abstract class for value ordering heuristics (Comparator<ConstraintNetwork>)
    used in backtracking search (e.g., MetaConstraintSolver)."""

    @abstractmethod
    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        """Negative if n1 sorts before n2, zero if equivalent, positive otherwise."""
