"""Port of framework/multi/MultiBinaryConstraint.java."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from metacsp.framework.multi.multi_constraint import MultiConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["MultiBinaryConstraint"]


class MultiBinaryConstraint(MultiConstraint):
    """A MultiConstraint whose scope always has size two."""

    def __init__(self) -> None:
        super().__init__()
        self.scope = [None, None]  # type: ignore[list-item]

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        return self.create_internal_constraints_from_to(variables[0], variables[1])

    @abstractmethod
    def create_internal_constraints_from_to(
        self, from_: Variable, to: Variable
    ) -> list[Constraint] | None:
        """Create the internal constraints underlying this
        MultiBinaryConstraint, between its source and destination Variable."""

    @property
    def from_(self) -> Variable:
        return self.scope[0]

    @from_.setter
    def from_(self, f: Variable) -> None:
        self.scope[0] = f

    @property
    def to(self) -> Variable:
        return self.scope[1]

    @to.setter
    def to(self, t: Variable) -> None:
        self.scope[1] = t

    def __str__(self) -> str:
        return f"({self.from_}) --{self.edge_label}--> ({self.to})"
