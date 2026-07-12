"""Port of meta/simplePlanner/Axiom.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint

__all__ = ["Axiom"]


class Axiom:
    """A named group of requirement activities plus a matrix of extra
    AllenIntervalConstraints among them (index 0 is reserved, mirroring
    :class:`~.simple_operator.SimpleOperator`'s ``extraConstraints`` layout,
    even though ``Axiom`` itself has no "head")."""

    def __init__(self, requirement_activities: list[str]) -> None:
        self.requirement_activities = requirement_activities
        n = len(requirement_activities) + 1
        self.extra_constraints: list[list[AllenIntervalConstraint | None]] = [
            [None] * n for _ in range(n)
        ]

    def add_constraint(self, c: AllenIntervalConstraint, from_: int, to: int) -> None:
        self.extra_constraints[from_][to] = c

    def __str__(self) -> str:
        extra_cons = ""
        if self.extra_constraints is not None:
            for i in range(1, len(self.extra_constraints)):
                for j in range(1, len(self.extra_constraints[i])):
                    con = self.extra_constraints[i][j]
                    if con is not None:
                        extra_cons += "\n" + self.requirement_activities[i - 1]
                        extra_cons += (
                            " --"
                            + str([t.name for t in con.types])
                            + " "
                            + str([str(b) for b in con.bounds])
                            + "--> "
                        )
                        extra_cons += self.requirement_activities[j - 1]

        if extra_cons.strip() != "":
            return extra_cons
        return ""
