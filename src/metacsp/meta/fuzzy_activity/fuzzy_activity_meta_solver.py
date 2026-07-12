"""Port of meta/fuzzyActivity/FuzzyActivityMetaSolver.java.

Provides a meta-CSP implementation of fuzzy context inference combining
fuzzy symbolic inference and fuzzy temporal inference, via
FuzzyActivityNetworkSolver. Uses Branch-and-Bound search
(:meth:`~metacsp.framework.meta.meta_constraint_solver.MetaConstraintSolver.
branch_and_bound`) to find the *optimal* unification of rules (see
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
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_variable import MetaVariable

__all__ = ["FuzzyActivityMetaSolver"]


class FuzzyActivityMetaSolver(MetaConstraintSolver):
    """A MetaConstraintSolver whose single ground solver is a
    FuzzyActivityNetworkSolver; uses Branch-and-Bound search to find the
    optimal unification of rules to FuzzyActivities."""

    def __init__(self, animation_time: int) -> None:
        super().__init__(
            [FuzzyAllenIntervalConstraint, SymbolicValueConstraint],
            animation_time,
            FuzzyActivityNetworkSolver(),
        )
        self.upper_bound = 0.0
        self.lower_bound = 0.0
        self.tmp_lower_bound = 0.0
        self.cn: ConstraintNetwork | None = None
        self.opt_cn: ConstraintNetwork | None = None
        self.value_consistency = 0.0
        self.temporal_consistency = 0.0
        self.vc_tmp = 0.0
        self.tc_tmp = 0.0

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
        domain = cast(FuzzyActivityDomain, self.meta_constraints[0])
        self.upper_bound = domain.get_consistency()
        self.cn = domain.get_constraint_network()
        self.vc_tmp = domain.get_value_consistency()
        self.tc_tmp = domain.get_temporal_consistency()
        self.tmp_lower_bound = self.upper_bound

    def get_lower_bound(self) -> float:
        return self.lower_bound

    def set_lower_bound(self) -> None:
        if self.tmp_lower_bound > self.lower_bound:
            self.lower_bound = self.tmp_lower_bound
            self.opt_cn = self.cn
            self.value_consistency = self.vc_tmp
            self.temporal_consistency = self.tc_tmp
            self.logger.debug("getLowebound: %s", self.lower_bound)

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        cons = cast(FuzzyActivityDomain, self.meta_constraints[0]).get_false_clause()
        for c1 in meta_value.get_constraints():
            for c2 in cons:
                if self._is_a_false_clause(c1, c2):
                    return True
        return False

    def reset_false_clause(self) -> None:
        cast(FuzzyActivityDomain, self.meta_constraints[0]).reset_false_clause()

    def _is_a_false_clause(self, c1: Constraint, c2: Constraint) -> bool:
        if c1.scope[0].id == c2.scope[0].id and c1.scope[1].id == c2.scope[1].id:
            return True
        # Java bug reproduced verbatim: the second disjunct compares
        # c1.scope[0].id against c2.scope[1].id on *both* sides (should
        # likely also check c1.scope[1].id == c2.scope[0].id), so it is
        # equivalent to `c1.scope[0].id == c2.scope[1].id`.
        if c1.scope[0].id == c2.scope[1].id and c1.scope[0].id == c2.scope[1].id:
            return True
        return False

    def get_optimal_constraint(self) -> ConstraintNetwork | None:
        return self.opt_cn

    def get_most_likely_occurred_activities(self) -> str:
        assert self.opt_cn is not None
        return cast(FuzzyActivityDomain, self.meta_constraints[0]).get_optimal_hypothesis(
            self.opt_cn, self.value_consistency, self.temporal_consistency
        )
