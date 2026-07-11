"""Port of framework/meta/NullConstraintNetwork.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.constraint_network import ConstraintNetwork

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["NullConstraintNetwork"]


class NullConstraintNetwork(ConstraintNetwork):
    """A special constraint network used to represent terminal (failure)
    nodes in the search space of a MetaConstraintSolver."""

    def __init__(self, sol: ConstraintSolver | None) -> None:
        super().__init__(sol)

    def __str__(self) -> str:
        return "conflicting"
