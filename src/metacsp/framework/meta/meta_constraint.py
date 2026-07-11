"""Port of framework/meta/MetaConstraint.java."""

from __future__ import annotations

import functools
from abc import abstractmethod
from typing import TYPE_CHECKING

from metacsp.framework.constraint import Constraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH

__all__ = ["MetaConstraint"]


class MetaConstraint(Constraint):
    """A generalization of the concept of constraint in classical CSPs.

    MetaConstraints represent requirements that must be upheld in a
    particular meta-CSP application domain (e.g., a resource in scheduling).
    They subsume ground-CSP constraints and are used to synthesize values for
    MetaVariables in a MetaConstraintSolver's backtracking search.
    """

    def __init__(self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None) -> None:
        super().__init__()
        self.var_oh = var_oh
        self.val_oh = val_oh
        self.meta_cs: MetaConstraintSolver | None = None
        self.independent_mc = False

    def set_meta_solver(self, meta_cs: MetaConstraintSolver) -> None:
        self.meta_cs = meta_cs
        self.logger.debug("Set MetaConstraintSolver to %s", meta_cs.description)

    def get_meta_variable(self) -> ConstraintNetwork | None:
        """The highest-priority MetaVariable according to this MetaConstraint's
        variable ordering heuristic."""
        vars_ = self.get_meta_variables()
        if vars_:
            if self.var_oh is not None:
                self.var_oh.collect_data(vars_)
                vars_ = sorted(vars_, key=functools.cmp_to_key(self.var_oh.compare))
            return vars_[0]
        return None

    @abstractmethod
    def get_meta_variables(self) -> list[ConstraintNetwork]:
        """All MetaVariables according to this MetaConstraint."""

    def get_meta_value(self, meta_variable: MetaVariable) -> ConstraintNetwork:
        """The best meta value for the given MetaVariable, as determined by
        this MetaConstraint's ValueOrderingH."""
        vals = self.get_meta_values(meta_variable)
        if self.val_oh is not None:
            vals = sorted(vals, key=functools.cmp_to_key(self.val_oh.compare))
        return vals[0]

    @abstractmethod
    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        """All meta values for the given MetaVariable."""

    @abstractmethod
    def mark_resolved_sub(self, meta_variable: MetaVariable, meta_value: ConstraintNetwork) -> None:
        """Mark a MetaVariable as solved by the given meta value."""

    @abstractmethod
    def draw(self, network: ConstraintNetwork) -> None:
        """Draw the meta-CSP's constraint network according to the rationale
        of this MetaConstraint."""

    @property
    def description(self) -> str:
        var_oh_name = type(self.var_oh).__name__ if self.var_oh is not None else "null"
        # Java bug reproduced verbatim: the valOH branch also reads varOH's class.
        val_oh_name = type(self.var_oh).__name__ if self.val_oh is not None else "null"
        return f"[{type(self).__name__} varOH: {var_oh_name} valOH: {val_oh_name}]"

    @abstractmethod
    def get_ground_solver(self) -> ConstraintSolver:
        """The/a ground solver for this MetaConstraint."""
