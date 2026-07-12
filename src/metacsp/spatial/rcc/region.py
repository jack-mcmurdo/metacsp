"""Port of spatial/RCC/Region.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.variable import Variable
from metacsp.spatial.rcc.rectangle import Rectangle

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain

__all__ = ["Region"]


class Region(Variable):
    """A variable for RCC-8/RCC2 reasoning, whose domain is a Rectangle."""

    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._dom: Domain = Rectangle(self)

    @property
    def domain(self) -> Domain:
        return self._dom

    @domain.setter
    def domain(self, d: Domain) -> None:
        self._dom = d

    def __str__(self) -> str:
        return f"{type(self).__name__} {self.id} {self.domain}"

    def __lt__(self, other: Variable) -> bool:
        return False
