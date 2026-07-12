"""Port of meta/simplePlanner/SimpleOperator.java."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from metacsp.exceptions import InvalidActivityException

if TYPE_CHECKING:
    from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint

__all__ = ["SimpleOperator"]


class SimpleOperator:
    """A planning operator: a head activity, a list of requirement
    activities each optionally linked to the head by an AllenIntervalConstraint,
    a matrix of "extra" AllenIntervalConstraints among head/requirements, and
    resource usage amounts."""

    class ReservedWord(Enum):
        """Keywords reserved by the ``.ddl`` domain-description grammar (see
        :meth:`~.simple_domain.SimpleDomain.parse_domain`)."""

        Head = auto()
        SimpleOperator = auto()
        PlanningOperator = auto()
        Resource = auto()
        Constraint = auto()
        SimpleDomain = auto()
        RequiredResource = auto()
        RequiredState = auto()
        AchievedState = auto()

    def __init__(
        self,
        head: str,
        requirement_constraints: list[AllenIntervalConstraint | None] | None,
        requirement_activities: list[str] | None,
        usages: list[int] | None,
    ) -> None:
        self.head = head
        if requirement_activities is not None:
            for a in requirement_activities:
                if a is not None and a == head:
                    raise InvalidActivityException(a)
        self.requirement_constraints = requirement_constraints
        self.requirement_activities = requirement_activities
        self.usages = usages
        if requirement_constraints is not None:
            assert requirement_activities is not None
            n = len(requirement_activities) + 1
            self.extra_constraints: list[list[AllenIntervalConstraint | None]] = [
                [None] * n for _ in range(n)
            ]
        else:
            self.extra_constraints = [[None]]

    def add_constraint(self, c: AllenIntervalConstraint, from_: int, to: int) -> None:
        self.extra_constraints[from_][to] = c

    def __str__(self) -> str:
        acts = ""
        if self.requirement_activities is not None:
            assert self.requirement_constraints is not None
            for i in range(len(self.requirement_activities)):
                if self.requirement_constraints[i] is not None:
                    con = self.requirement_constraints[i]
                    assert con is not None
                    acts += (
                        self.head
                        + " --"
                        + str([t.name for t in con.types])
                        + " "
                        + str([str(b) for b in con.bounds])
                        + "--> "
                        + self.requirement_activities[i]
                    )
                if i != len(self.requirement_activities) - 1:
                    acts += "\n"

        ret = ""
        if acts.strip() != "":
            ret += acts

        extra_cons = ""
        if self.extra_constraints is not None:
            for i in range(len(self.extra_constraints)):
                for j in range(len(self.extra_constraints[i])):
                    con = self.extra_constraints[i][j]
                    if con is not None:
                        if i == 0:
                            extra_cons += "\n" + self.head
                        else:
                            assert self.requirement_activities is not None
                            extra_cons += "\n" + self.requirement_activities[i - 1]
                        extra_cons += (
                            " --"
                            + str([t.name for t in con.types])
                            + " "
                            + str([str(b) for b in con.bounds])
                            + "--> "
                        )
                        if j == 0:
                            extra_cons += self.head
                        else:
                            assert self.requirement_activities is not None
                            extra_cons += self.requirement_activities[j - 1]
        if extra_cons.strip() != "":
            ret += extra_cons

        if self.usages is not None:
            if acts.strip() != "":
                ret += "\n"
            ret += self.head + " usage: " + str(self.usages)

        return ret
