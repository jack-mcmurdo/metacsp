"""Port of meta/symbolsAndTime/Scheduler.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_variable import MetaVariable

__all__ = ["Scheduler"]


class Scheduler(MetaConstraintSolver):
    """A MetaConstraintSolver whose single ground solver is an
    ActivityNetworkSolver; MetaConstraints added to it (e.g.
    ReusableResource, StateVariable) arbitrate access to shared resources by
    posting AllenIntervalConstraints between conflicting Activities."""

    def __init__(
        self,
        origin: int,
        horizon: int,
        animation_time: int,
        num_activities: int | None = None,
    ) -> None:
        if num_activities is None:
            ground_solver = ActivityNetworkSolver(origin, horizon, 500)
        else:
            ground_solver = ActivityNetworkSolver(origin, horizon, num_activities)
        super().__init__(
            [AllenIntervalConstraint, SymbolicValueConstraint], animation_time, ground_solver
        )

    def pre_backtrack(self) -> None:
        """No-op: Scheduler needs no extra bookkeeping before branching."""
        pass

    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        """No-op: Scheduler needs no extra bookkeeping when retracting a resolver."""
        pass

    def add_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> bool:
        """Always True: resolvers are always accepted before ground-CSP propagation."""
        return True

    def post_backtrack(self, mv: MetaVariable) -> None:
        """No-op: Scheduler needs no extra bookkeeping after branching."""
        pass

    def get_upper_bound(self) -> float:
        """Always 0.0: Scheduler does not support branch-and-bound optimization."""
        return 0.0

    def set_upper_bound(self) -> None:
        """No-op: Scheduler does not support branch-and-bound optimization."""
        pass

    def get_lower_bound(self) -> float:
        """Always 0.0: Scheduler does not support branch-and-bound optimization."""
        return 0.0

    def set_lower_bound(self) -> None:
        """No-op: Scheduler does not support branch-and-bound optimization."""
        pass

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        """Always False: Scheduler does not support branch-and-bound optimization."""
        return False

    def reset_false_clause(self) -> None:
        """No-op: Scheduler does not support branch-and-bound optimization."""
        pass
