"""Port of meta/symbolsAndTime/StateVariableScheduler.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_variable import MetaVariable

__all__ = ["StateVariableScheduler"]


class StateVariableScheduler(MetaConstraintSolver):
    """A MetaConstraintSolver whose single ground solver is an
    ActivityNetworkSolver, intended for use with StateVariable
    MetaConstraints."""

    def __init__(self, origin: int, horizon: int, animation_time: int) -> None:
        super().__init__(
            [AllenIntervalConstraint, SymbolicValueConstraint],
            animation_time,
            ActivityNetworkSolver(origin, horizon),
        )

    def pre_backtrack(self) -> None:
        pass

    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        pass

    def add_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> bool:
        return True

    def post_backtrack(self, mv: MetaVariable) -> None:
        pass

    def get_upper_bound(self) -> float:
        return 0.0

    def set_upper_bound(self) -> None:
        pass

    def get_lower_bound(self) -> float:
        return 0.0

    def set_lower_bound(self) -> None:
        pass

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        return False

    def reset_false_clause(self) -> None:
        pass
