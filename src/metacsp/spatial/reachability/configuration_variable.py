"""Port of spatial/reachability/ConfigurationVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.variable import Variable
from metacsp.spatial.reachability.configuration_domain import ConfigurationDomain

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain

__all__ = ["ConfigurationVariable"]


class ConfigurationVariable(Variable):
    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._dom: Domain | None = None
        self.domain = ConfigurationDomain(self)

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    @property
    def domain(self) -> Domain | None:
        return self._dom

    @domain.setter
    def domain(self, d: Domain) -> None:
        self._dom = d

    def __str__(self) -> str:
        return f"{type(self).__name__} {self.id} {self.domain}"
