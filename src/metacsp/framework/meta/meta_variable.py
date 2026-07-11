"""Port of framework/meta/MetaVariable.java.

MetaVariables are used internally by MetaConstraintSolver and should not be
instantiated directly by client code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_constraint import MetaConstraint

__all__ = ["MetaVariable"]


class MetaVariable:
    """A search-space node used by MetaConstraintSolver for backtracking search.

    Wraps a ConstraintNetwork representing the meta-variable, together with a
    reference to the MetaConstraint that produced it.
    """

    def __init__(
        self,
        meta_constraint: MetaConstraint | None,
        constraint_network: ConstraintNetwork | None,
        annotation: str | None = None,
    ) -> None:
        self.meta_constraint = meta_constraint
        self.mv = constraint_network
        self.annotation = annotation

    @property
    def constraint_network(self) -> ConstraintNetwork | None:
        return self.mv

    def __str__(self) -> str:
        ret = f"[{self.meta_constraint}] "
        assert self.mv is not None
        variables = self.mv.get_variables()
        if variables:
            ret += f"Vars = {variables}"
        constraints = self.mv.get_constraints()
        if constraints:
            ret += f" Cons = {constraints}"
        if self.annotation is not None:
            ret += f" ({self.annotation})"
        return ret
