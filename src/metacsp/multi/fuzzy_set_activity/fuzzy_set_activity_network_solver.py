"""Port of multi/fuzzySetActivity/FuzzySetActivityNetworkSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.fuzzy_symbols.fuzzy_symbolic_variable_constraint_solver import (
    FuzzySymbolicVariableConstraintSolver,
)
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.multi.fuzzy_set_activity.fuzzy_set_activity import FuzzySetActivity
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["FuzzySetActivityNetworkSolver"]


class FuzzySetActivityNetworkSolver(MultiConstraintSolver):
    """A MultiConstraintSolver over FuzzySetActivities: a combination of a
    (crisp) AllenIntervalNetworkSolver and a
    FuzzySymbolicVariableConstraintSolver."""

    MAX_ACTIVITIES: ClassVar[int] = 500

    def __init__(self, origin: int, horizon: int, num_acts: int | None = None) -> None:
        if num_acts is None:
            solvers = self._create_constraint_solvers(origin, horizon)
        else:
            solvers = self._create_constraint_solvers_with_num_acts(origin, horizon, num_acts)
            FuzzySetActivityNetworkSolver.MAX_ACTIVITIES = num_acts
        super().__init__(
            [AllenIntervalConstraint, SymbolicValueConstraint], FuzzySetActivity, solvers, [1, 1]
        )
        self.origin = origin
        self.horizon = horizon

    @property
    def rigidity_number(self) -> float:
        """The rigidity number of the underlying APSPSolver's ConstraintNetwork."""
        return cast(AllenIntervalNetworkSolver, self.constraint_solvers[0]).rigidity_number

    @staticmethod
    def _create_constraint_solvers_with_num_acts(
        origin: int, horizon: int, num_acts: int
    ) -> list[ConstraintSolver]:
        return [
            AllenIntervalNetworkSolver(origin, horizon, num_acts),
            FuzzySymbolicVariableConstraintSolver(),
        ]

    @staticmethod
    def _create_constraint_solvers(origin: int, horizon: int) -> list[ConstraintSolver]:
        return [
            AllenIntervalNetworkSolver(origin, horizon),
            FuzzySymbolicVariableConstraintSolver(),
        ]

    def propagate(self) -> bool:
        # Does nothing... everything is done by the two underlying solvers
        # (AllenIntervalNetworkSolver and FuzzySymbolicVariableConstraintSolver).
        return True

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
