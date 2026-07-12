"""Port of spatial/reachability/ReachabilityConstraint.java."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from metacsp.framework.binary_constraint import BinaryConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["ReachabilityConstraint"]


class ReachabilityConstraint(BinaryConstraint):
    """A binary constraint stating that a configuration is reachable relative to
    another, for a given reachability purpose."""

    class Type(Enum):
        none = 0
        activityReachable = 1
        basePickingupReachable = 2
        baseplacingReachable = 3

    def __init__(self, *types: Type) -> None:
        super().__init__()
        self.types: list[ReachabilityConstraint.Type] = list(types)

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> ReachabilityConstraint:
        return ReachabilityConstraint(*self.types)

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def __str__(self) -> str:
        ret = "["
        for t in self.types:
            ret += f"({self.from_}) --{t.name}--> ({self.to})"
        ret += "]"
        return ret
