"""Port of time/Bounds.java.

``INF``/``print_long`` are defined here (rather than in ``apsp_solver.py``,
which is where Java's ``APSPSolver.INF``/``APSPSolver.printLong`` live) to
avoid a module cycle: ``Bounds.toString()`` calls ``APSPSolver.printLong``,
while ``APSPSolver`` and ``SimpleDistanceConstraint`` both need ``INF``.
``apsp_solver.py`` re-exposes both as ``APSPSolver.INF``/``APSPSolver.print_long``
for call-site fidelity (D3).
"""

from __future__ import annotations

from functools import total_ordering

__all__ = ["Bounds", "INF", "print_long"]

INF = 2**61


def print_long(value: int) -> str:
    """Pretty-print a long, substituting +/-INF appropriately."""
    if value >= 0:
        return "INF" if value == INF else str(value)
    return "-INF" if -value == INF else str(value)


@total_ordering
class Bounds:
    """A general purpose min/max value pair."""

    def __init__(self, min: int, max: int) -> None:
        if min > max:
            raise ValueError(f"Invalid arguments, min > max, : ({min} > {max})")
        self.min = min
        self.max = max

    @property
    def is_singleton(self) -> bool:
        return self.min == self.max

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Bounds):
            return self.min == other.min and self.max == other.max
        return False

    def __hash__(self) -> int:
        return hash((self.min, self.max))

    def __str__(self) -> str:
        return f"[{print_long(self.min)}, {print_long(self.max)}]"

    __repr__ = __str__

    def intersect_strict(self, b: Bounds) -> Bounds | None:
        """Intersection treating singleton intervals [n,n] as empty -- needed
        for scheduling intersections where "a meets b" should not conflict."""
        _min = max(self.min, b.min)
        _max = min(self.max, b.max)
        if _min < _max:
            return Bounds(_min, _max)
        return None

    def is_intersecting(self, b: Bounds) -> bool:
        return self.intersect_strict(b) is not None

    def intersect(self, b: Bounds) -> Bounds | None:
        _min = max(self.min, b.min)
        _max = min(self.max, b.max)
        if _min <= _max:
            return Bounds(_min, _max)
        return None

    @staticmethod
    def union(*b: Bounds) -> Bounds | None:
        _min = INF - 1
        _max = -INF + 1
        for bounds in b:
            _min = min(_min, bounds.min)
            _max = max(_max, bounds.max)
        if _min <= _max:
            return Bounds(_min, _max)
        return None

    def compare_to(self, o: Bounds) -> int:
        def signum(x: int) -> int:
            return (x > 0) - (x < 0)

        return 2 * signum(o.min - self.min) + 1 * signum(o.max - self.max)

    def __lt__(self, other: Bounds) -> bool:
        return self.compare_to(other) < 0
