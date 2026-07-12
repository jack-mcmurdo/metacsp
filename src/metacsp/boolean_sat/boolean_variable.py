"""Port of booleanSAT/BooleanVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.boolean_sat.boolean_domain import BooleanDomain
from metacsp.framework.domain import Domain
from metacsp.framework.variable import Variable

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["BooleanVariable"]


class BooleanVariable(Variable):
    """A Boolean variable (domain {T,F}) for use with
    BooleanSatisfiabilitySolver and BooleanConstraints."""

    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._domain: Domain = BooleanDomain(self, True, True)

    def allow_true(self) -> None:
        cast(BooleanDomain, self.domain).allow_true()

    def allow_false(self) -> None:
        cast(BooleanDomain, self.domain).allow_false()

    def __lt__(self, other: Variable) -> bool:
        # Mirrors the Java source, which passes `other` (a Variable) where
        # BooleanDomain.compareTo expects a BooleanDomain -- the instanceof
        # check inside always fails, so compareTo (and thus this ordering)
        # is always "equal" (never less-than).
        return False

    @property
    def domain(self) -> Domain:
        return self._domain

    @domain.setter
    def domain(self, d: Domain) -> None:
        self._domain = d

    def __str__(self) -> str:
        return f"x{self.id} {self.domain}"
