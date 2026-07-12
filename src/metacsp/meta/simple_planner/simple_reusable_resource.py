"""Port of meta/simplePlanner/SimpleReusableResource.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.meta.symbols_and_time.schedulable import Schedulable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.meta.simple_planner.simple_domain import SimpleDomain
    from metacsp.multi.activity.activity import Activity

__all__ = ["SimpleReusableResource"]


class SimpleReusableResource(Schedulable):
    """A Schedulable representing a resource of a given integer capacity
    whose usage levels are looked up in a SimpleDomain (as opposed to
    :class:`~metacsp.meta.symbols_and_time.reusable_resource.ReusableResource`,
    which infers usage from the Activity's own symbol)."""

    def __init__(
        self,
        var_oh: VariableOrderingH | None,
        val_oh: ValueOrderingH | None,
        capacity: int,
        rd: SimpleDomain,
        name: str,
    ) -> None:
        super().__init__(var_oh, val_oh)
        self.capacity = capacity
        self.rd = rd
        self.name = name

    def is_conflicting(self, peak: list[Activity]) -> bool:
        """True iff the peak's total resource usage (per the SimpleDomain) exceeds capacity."""
        total = 0
        for act in peak:
            total += self.rd.get_resource_usage_level(self, act.variable)
            if total > self.capacity:
                return True
        return False

    def draw(self, network: ConstraintNetwork) -> None:
        """No-op: SimpleReusableResource has no dedicated visualization."""
        pass

    def __str__(self) -> str:
        return f"SimpleReusableResource {self.name}, capacity = {self.capacity}"

    @property
    def edge_label(self) -> str | None:
        """Always None: SimpleReusableResource is not drawn as a graph edge."""
        return None

    def clone(self) -> SimpleReusableResource | None:
        """Always None: SimpleReusableResource does not support cloning."""
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        """Always False: SimpleReusableResource has no notion of equivalence."""
        return False

    def get_ground_solver(self) -> ConstraintSolver | None:
        """Always None: SimpleReusableResource has no single ground solver of its own."""
        return None
