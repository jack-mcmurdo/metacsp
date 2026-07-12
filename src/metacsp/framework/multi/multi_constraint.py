"""Port of framework/multi/MultiConstraint.java."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from metacsp.framework.constraint import Constraint

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["MultiConstraint"]


class MultiConstraint(Constraint):
    """A constraint among Variables (which could be MultiVariables), itself
    "implemented" by one or more lower-level constraints."""

    def __init__(self) -> None:
        super().__init__()
        self._internal_constraints: list[Constraint] | None = None
        self._propagate_immediately = True

    @abstractmethod
    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        """Instantiate the internal constraints underlying this
        MultiConstraint, given the Variables in its scope."""

    @property
    def internal_constraints(self) -> list[Constraint] | None:
        """The lower-level constraints implementing this MultiConstraint (created lazily)."""
        if self._internal_constraints is None:
            self._internal_constraints = self.create_internal_constraints(self.scope)
        return self._internal_constraints

    def set_propagate_later(self) -> None:
        """Delay propagation of this MultiConstraint."""
        self._propagate_immediately = False

    def set_propagate_immediately(self) -> None:
        """Schedule this MultiConstraint for immediate propagation."""
        self._propagate_immediately = True

    def propagate_immediately(self) -> bool:
        """True iff this constraint should be propagated as soon as it is
        added (the default)."""
        return self._propagate_immediately

    @property
    def description(self) -> str:
        """Human-readable description listing this constraint's internal constraint types."""
        ret = f"{type(self).__name__}: ["
        if self.internal_constraints is not None:
            ret += ",".join(type(con).__name__ for con in self.internal_constraints)
        return ret + "]"
