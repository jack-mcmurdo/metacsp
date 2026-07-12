"""Port of time/qualitative/SimpleAllenInterval.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain
from metacsp.framework.variable import Variable
from metacsp.time.qualitative.simple_interval import SimpleInterval

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["SimpleAllenInterval"]


class SimpleAllenInterval(Variable):
    """An Allen interval variable used for qualitative temporal reasoning
    (e.g. by QualitativeAllenSolver), as opposed to AllenInterval which
    represents an interval as two TimePoints for quantitative reasoning."""

    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._domain: Domain = SimpleInterval(self)

    @property
    def domain(self) -> Domain:
        """This SimpleAllenInterval's Domain."""
        return self._domain

    @domain.setter
    def domain(self, d: Domain) -> None:
        """Set this SimpleAllenInterval's Domain."""
        self._domain = d

    def __str__(self) -> str:
        return f"{type(self).__name__} {self.id} {self.domain}"

    def __lt__(self, other: Variable) -> bool:
        return False
