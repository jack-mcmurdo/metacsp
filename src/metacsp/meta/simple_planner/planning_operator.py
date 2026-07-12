"""Port of meta/simplePlanner/PlanningOperator.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.meta.simple_planner.simple_operator import SimpleOperator

if TYPE_CHECKING:
    from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint

__all__ = ["PlanningOperator"]


class PlanningOperator(SimpleOperator):
    """A SimpleOperator whose requirement activities are each additionally
    tagged as an effect (achieved state) or not (required state)."""

    def __init__(
        self,
        head: str,
        requirement_constraints: list[AllenIntervalConstraint | None] | None,
        requirement_activities: list[str] | None,
        effects: list[bool],
        usages: list[int] | None,
    ) -> None:
        super().__init__(head, requirement_constraints, requirement_activities, usages)
        self.effects = effects

    def is_effect(self, requirement: str) -> bool:
        if self.requirement_activities is not None:
            for i in range(len(self.requirement_activities)):
                if self.requirement_activities[i] == requirement:
                    return self.effects[i]
        return False
