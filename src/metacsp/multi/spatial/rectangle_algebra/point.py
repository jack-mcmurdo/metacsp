"""Port of multi/spatial/rectangleAlgebra/Point.java."""

from __future__ import annotations

import math

__all__ = ["Point"]


class Point:
    """A 2D or (optionally) 3D point with double-precision coordinates.

    Java's fields ``x``/``y``/``z`` and its getters ``getX()``/``getY()``/
    ``getZ()`` are redundant (both simply expose the public field) -- only
    the ``x``/``y``/``z`` attributes are kept here, per C2, since a Python
    attribute already serves as both.
    """

    def __init__(self, x: float, y: float, z: float | None = None) -> None:
        self.x = x
        self.y = y
        self.z = z if z is not None else 0.0
        self._is_3d = z is not None

    def x_int(self) -> int:
        """Java's zero-arg method ``x()``: ``x`` rounded to the nearest int
        (ties round away from zero, matching ``Math.abs(intValue()-x) < 0.5``).

        Renamed from Java's ``x()`` (likewise ``y()``/``z()`` below) because
        Java allows a field and a same-named zero-arg method to coexist
        (different namespaces: ``p.x`` vs ``p.x()``) while Python cannot --
        an attribute and a method can't share one name on the same object.
        Verified unused anywhere else in the pinned Java commit, so the
        rename has no observable effect on ported behavior.
        """
        return _round_half_away_from_zero(self.x)

    def y_int(self) -> int:
        return _round_half_away_from_zero(self.y)

    def z_int(self) -> int:
        return _round_half_away_from_zero(self.z)

    def __str__(self) -> str:
        if self._is_3d:
            return f"({self.x},{self.y},{self.z})"
        return f"({self.x},{self.y})"

    def distance(self, p: Point) -> float:
        return math.sqrt((p.x - self.x) ** 2 + (p.y - self.y) ** 2)


def _round_half_away_from_zero(value: float) -> int:
    truncated = int(value)  # Java's (int)(double) cast: truncates toward zero.
    if abs(truncated - value) < 0.5:
        return truncated
    return truncated + 1
