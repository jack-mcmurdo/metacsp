"""Port of time/Interval.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.time.time_point import TimePoint

__all__ = ["Interval"]


class Interval(Domain):
    """Represents intervals of time described by a start and an end time.

    Used as a domain for APSPSolver variables (TimePoints), and also as a
    utility class to represent intervals (e.g., for constraints).
    """

    def __init__(self, time_point: TimePoint, start: int = 0, stop: int = 0) -> None:
        super().__init__(time_point)
        self.bounds = Bounds(start, stop)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Interval) and self.compare_to(other) == 0

    def __hash__(self) -> int:
        return hash(self.bounds)

    def __str__(self) -> str:
        return str(self.bounds)

    def compare_to(self, other: Interval) -> int:
        return self.bounds.compare_to(other.bounds)

    @property
    def lower_bound(self) -> int:
        return self.bounds.min

    @property
    def upper_bound(self) -> int:
        return self.bounds.max
