"""Port of framework/VariableOrderingH.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork

__all__ = ["VariableOrderingH"]


class VariableOrderingH(ABC):
    """Abstract class for variable ordering heuristics (Comparator<ConstraintNetwork>)
    used in backtracking search (e.g., MetaConstraintSolver)."""

    @abstractmethod
    def collect_data(self, all_meta_variables: Sequence[ConstraintNetwork]) -> None: ...

    @abstractmethod
    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        """Negative if n1 sorts before n2, zero if equivalent, positive otherwise."""
