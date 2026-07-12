"""Port of meta/symbolsAndTime/ReusableResource.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.meta.symbols_and_time.schedulable import Schedulable
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.multi.activity.activity import Activity

__all__ = ["ReusableResource"]


class ReusableResource(Schedulable):
    """A Schedulable representing a resource of a given integer capacity:
    a peak of Activities conflicts iff the sum of their (integer,
    single-symbol) usage exceeds the capacity."""

    def __init__(
        self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None, capacity: int
    ) -> None:
        super().__init__(var_oh, val_oh)
        self.capacity = capacity

    def is_conflicting(self, peak: list[Activity]) -> bool:
        total = 0
        for act in peak:
            sva = cast(SymbolicVariableActivity, act.variable)
            total += int(sva.symbolic_variable.symbols[0])
            if total > self.capacity:
                return True
        return False

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def __str__(self) -> str:
        return type(self).__name__

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> ReusableResource | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def get_ground_solver(self) -> ConstraintSolver | None:
        return None
