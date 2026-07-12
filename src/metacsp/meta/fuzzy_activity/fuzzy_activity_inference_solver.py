"""Port of meta/fuzzyActivity/FuzzyActivityInferenceSolver.java.

Provides a meta-CSP implementation of fuzzy context inference combining
fuzzy symbolic inference (FuzzySymbolicVariableConstraintSolver) and fuzzy
temporal inference (FuzzyAllenIntervalNetworkSolver), via
FuzzyActivityNetworkSolver. Uses plain backtracking search (see
:class:`~.fuzzy_activity_meta_solver.FuzzyActivityMetaSolver` for the
Branch-and-Bound variant) to find a possible unification of rules (see
:class:`~.fuzzy_activity_domain.FuzzyActivityDomain`) to existing
FuzzyActivity variables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.meta.fuzzy_activity.fuzzy_activity_domain import FuzzyActivityDomain
from metacsp.multi.fuzzy_activity.fuzzy_activity_network_solver import FuzzyActivityNetworkSolver
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_variable import MetaVariable

__all__ = ["FuzzyActivityInferenceSolver"]


class FuzzyActivityInferenceSolver(MetaConstraintSolver):
    """A MetaConstraintSolver whose single ground solver is a
    FuzzyActivityNetworkSolver; uses plain backtracking search (as opposed
    to :class:`~.fuzzy_activity_meta_solver.FuzzyActivityMetaSolver`'s
    branch-and-bound) to find a unification of rules to FuzzyActivities."""

    def __init__(self, animation_time: int) -> None:
        super().__init__(
            [FuzzyAllenIntervalConstraint, SymbolicValueConstraint],
            animation_time,
            FuzzyActivityNetworkSolver(),
        )
        self.upper_bound = 0.0
        self.lower_bound = -1.0
        self.tmp_lower_bound = -1.0

    def pre_backtrack(self) -> None:
        pass

    def post_backtrack(self, mv: MetaVariable) -> None:
        pass

    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        cast(FuzzyActivityDomain, self.meta_constraints[0]).set_unjustified(meta_variable)

    def add_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> bool:
        return True

    def get_upper_bound(self) -> float:
        return self.upper_bound

    def set_upper_bound(self) -> None:
        self.upper_bound = cast(FuzzyActivityDomain, self.meta_constraints[0]).get_consistency()
        self.tmp_lower_bound = self.upper_bound
        self.logger.debug("getupperbound: %s", self.upper_bound)

    def get_lower_bound(self) -> float:
        return self.lower_bound

    def set_lower_bound(self) -> None:
        if self.tmp_lower_bound > self.lower_bound:
            self.lower_bound = self.tmp_lower_bound
        self.logger.debug("getLowebound: %s", self.lower_bound)

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        return False

    def reset_false_clause(self) -> None:
        pass
