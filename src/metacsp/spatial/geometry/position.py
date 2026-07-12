"""Port of spatial/geometry/Position.java."""

from __future__ import annotations

__all__ = ["Position"]


class Position:
    """A 2D (x, y) position, used by the geometry package's physics types."""

    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y
