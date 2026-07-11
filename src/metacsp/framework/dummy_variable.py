"""Port of framework/DummyVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from metacsp.framework.domain import Domain
from metacsp.framework.variable import Variable

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["DummyVariable"]


class _DummyDomain(Domain):
    """Private nested placeholder domain (Java DummyVariable.DummyDomain)."""

    def __str__(self) -> str:
        return ""


class DummyVariable(Variable):
    """Placeholder variable used by ConstraintNetwork to represent hyperedges
    (n-ary constraints) as a star of binary DummyConstraint edges."""

    _dummy_ids: ClassVar[int] = 0

    def __init__(self, cs: ConstraintSolver, label: str) -> None:
        super().__init__(cs, DummyVariable._dummy_ids)
        DummyVariable._dummy_ids += 1
        self.color = "lightgray"
        self.label = label

    def __lt__(self, other: Variable) -> bool:
        return False

    @property
    def domain(self) -> Domain:
        return _DummyDomain(self)

    @domain.setter
    def domain(self, d: Domain) -> None:
        pass

    def __str__(self) -> str:
        return self.label
