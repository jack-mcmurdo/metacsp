"""Port of onLineMonitoring/Hypothesis.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.time.bounds import INF, Bounds

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.variable import Variable
    from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity
    from metacsp.multi.fuzzy_activity.simple_timeline import SimpleTimeline
    from metacsp.online_monitoring.rule import Rule

__all__ = ["Hypothesis"]

Type = FuzzyAllenIntervalConstraint.Type


class Hypothesis:
    """One candidate inference of a :class:`~metacsp.online_monitoring.rule
    .Rule`'s head value, built from one particular unification of the
    rule's requirements with the current sensor readings."""

    def __init__(
        self,
        tc: float,
        vc: float,
        cn: ConstraintNetwork,
        r: Rule,
        head: Variable,
        pass_: int,
    ) -> None:
        self.temporal_consistency = tc
        self.value_consistency = vc
        self.constraint_network = cn
        self.rule = r
        self.head = head
        self.pass_ = pass_
        self.id = 0

    @property
    def overall_consistency(self) -> float:
        return min(self.temporal_consistency, self.value_consistency)

    def to_compact_string(self) -> str:
        head_i = -1
        max_poss = -1.0
        for i, p in enumerate(self.rule.possibilities):
            if p > max_poss:
                max_poss = p
                head_i = i
        return (
            f"{self.rule.component.name}={self.rule.component.states[head_i]} "
            f"(T,V)=({self.temporal_consistency}, {self.value_consistency})"
        )

    def __str__(self) -> str:
        head_i = -1
        max_poss = -1.0
        for i, p in enumerate(self.rule.possibilities):
            if p > max_poss:
                max_poss = p
                head_i = i
        return (
            f"{self.rule.component.name} {self.rule.component.states[head_i]}\n"
            f"\t(Temporal, Value) consistency: "
            f"({self.temporal_consistency}, {self.value_consistency}) "
            f"TOT: {self.overall_consistency}"
        )

    def get_interval(self, tls: dict[str, SimpleTimeline]) -> Bounds:
        """The tightest [start,end] interval consistent with this
        hypothesis's temporal constraints against the sensor timelines."""
        min_start: list[int] = []
        min_end: list[int] = []
        max_start: list[int] = []
        max_end: list[int] = []

        for con in self.constraint_network.get_constraints():
            if isinstance(con, FuzzyAllenIntervalConstraint):
                fc = con
                act: FuzzyActivity = fc.to  # type: ignore[assignment]
                tl = tls[act.component]  # type: ignore[index]
                start = tl.get_start(act)
                end = tl.get_end(act)

                if fc.contains_type(Type.After):
                    min_start.append(end + 1)
                if fc.contains_type(Type.Before):
                    max_end.append(start - 1)
                if fc.contains_type(Type.Contains):
                    max_start.append(start - 1)
                    min_end.append(end + 1)
                if fc.contains_type(Type.During):
                    min_start.append(start + 1)
                    max_end.append(end - 1)
                if fc.contains_type(Type.Equals):
                    min_start.append(start)
                    max_start.append(start)
                    min_end.append(end)
                    max_end.append(end)
                # |----------| A FinishedBy
                #     |------| B
                if fc.contains_type(Type.FinishedBy):
                    max_start.append(start - 1)
                    min_end.append(end)
                    max_end.append(end)
                #     |------| A Finishes
                # |----------| B
                if fc.contains_type(Type.Finishes):
                    min_start.append(start + 1)
                    min_end.append(end)
                    max_end.append(end)
                if fc.contains_type(Type.Meets):
                    max_end.append(start)
                    min_end.append(start)
                if fc.contains_type(Type.MetBy):
                    min_start.append(end)
                    max_start.append(end)
                #     |------| A OverlappedBy
                # |------|     B
                if fc.contains_type(Type.OverlappedBy):
                    max_start.append(end - 1)
                    min_start.append(start + 1)
                    min_end.append(end + 1)  # Iran
                # |------|     A Overlaps
                #     |------| B
                if fc.contains_type(Type.Overlaps):
                    min_end.append(start + 1)
                    max_end.append(end - 1)
                    max_start.append(start - 1)  # Iran
                # |-----------| A StartedBy
                # |------|      B
                if fc.contains_type(Type.StartedBy):
                    min_start.append(start)
                    max_start.append(start)
                    min_end.append(end + 1)
                # |------|      A Starts
                # |-----------| B
                if fc.contains_type(Type.Starts):
                    min_start.append(start)
                    max_start.append(start)
                    max_end.append(end - 1)

        try:
            earliest_start = min(min_start)
        except ValueError:
            earliest_start = 0

        try:
            latest_end = max(max_end)
        except ValueError:
            latest_end = INF

        try:
            latest_start = max(max_start)
        except ValueError:
            latest_start = earliest_start

        try:
            earliest_end = min(min_end)
        except ValueError:
            earliest_end = latest_end

        try:
            return Bounds(latest_start, earliest_end)
        except ValueError:
            try:
                return Bounds(earliest_start, earliest_end)
            except ValueError:
                try:
                    return Bounds(earliest_start, latest_end)
                except ValueError:
                    # Should occur only if TC < 1.0.
                    return Bounds(min(earliest_start, latest_end), max(earliest_start, latest_end))

    def __lt__(self, other: Hypothesis) -> bool:
        # Java compareTo: returns -1 (i.e. "less", sorts first) when this
        # Hypothesis has *greater* overall consistency -- Arrays.sort thus
        # yields a descending-by-consistency order.
        return self.overall_consistency > other.overall_consistency
