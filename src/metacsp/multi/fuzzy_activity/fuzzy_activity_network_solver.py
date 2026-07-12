"""Port of multi/fuzzyActivity/FuzzyActivityNetworkSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_network_solver import (
    FuzzyAllenIntervalNetworkSolver,
)
from metacsp.fuzzy_symbols.fuzzy_symbolic_variable_constraint_solver import (
    FuzzySymbolicVariableConstraintSolver,
)
from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["FuzzyActivityNetworkSolver"]


class FuzzyActivityNetworkSolver(MultiConstraintSolver):
    """A MultiConstraintSolver over FuzzyActivities: a combination of a
    FuzzyAllenIntervalNetworkSolver (fuzzy temporal placement) and a
    FuzzySymbolicVariableConstraintSolver (fuzzy symbolic value)."""

    def __init__(self) -> None:
        super().__init__(
            [FuzzyAllenIntervalConstraint, SymbolicValueConstraint],
            FuzzyActivity,
            self._create_constraint_solvers(),
            [1, 1],
        )

    @staticmethod
    def _create_constraint_solvers() -> list[ConstraintSolver]:
        return [FuzzyAllenIntervalNetworkSolver(), FuzzySymbolicVariableConstraintSolver()]

    def propagate(self) -> bool:
        # Does nothing... everything is done by the two underlying solvers
        # (FuzzyAllenIntervalNetworkSolver and FuzzySymbolicVariableConstraintSolver).
        return True

    def set_var_of_sub_graph(self, fas: list[FuzzyActivity]) -> None:
        cast(
            FuzzySymbolicVariableConstraintSolver, self.constraint_solvers[1]
        ).set_var_of_sub_graph(fas)
        cast(FuzzyAllenIntervalNetworkSolver, self.constraint_solvers[0]).set_var_of_sub_graph(fas)

    def get_temporal_consistency(self) -> float:
        return cast(
            FuzzyAllenIntervalNetworkSolver, self.constraint_solvers[0]
        ).get_posibility_degree()

    def get_value_consistency(self) -> float:
        return cast(
            FuzzySymbolicVariableConstraintSolver, self.constraint_solvers[1]
        ).get_upper_bound()

    def get_false_clause(self) -> list[Constraint]:
        return cast(
            FuzzySymbolicVariableConstraintSolver, self.constraint_solvers[1]
        ).get_false_constraint()

    def reset_false_clauses(self) -> None:
        cast(
            FuzzySymbolicVariableConstraintSolver, self.constraint_solvers[1]
        ).reset_false_clauses()

    def set_crisp_cons(self, crisp_cons: list[Constraint]) -> None:
        cast(FuzzyAllenIntervalNetworkSolver, self.constraint_solvers[0]).set_crisp_cons(crisp_cons)
