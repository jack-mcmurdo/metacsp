"""Port of framework/BinaryConstraint.java."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from metacsp.framework.constraint import Constraint

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["BinaryConstraint"]


class BinaryConstraint(Constraint, ABC):
    """Basic abstract class for constraints whose scope is of size two."""

    def __init__(self) -> None:
        super().__init__()
        self.scope = [None, None]  # type: ignore[list-item]

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
