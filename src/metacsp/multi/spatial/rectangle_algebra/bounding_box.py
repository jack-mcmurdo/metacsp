"""Port of multi/spatial/rectangleAlgebra/BoundingBox.java."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from metacsp.multi.spatial.rectangle_algebra.point import Point
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.multi.spatial.block_algebra.rectangular_cuboid import RectangularCuboid

__all__ = ["BoundingBox"]


def _trunc_div(a: int, b: int) -> int:
    """Integer division truncating toward zero, matching Java's ``/`` on
    ``long`` operands (Python's ``//`` floors toward negative infinity,
    which differs from Java for negative operands)."""
    q, r = divmod(a, b)
    if r != 0 and (a < 0) != (b < 0):
        q += 1
    return q


@dataclass
class AwtRectangle:
    """A minimal stand-in for ``java.awt.Rectangle``, used only by
    :class:`BoundingBox`'s plotting/filtering helpers (not part of the
    ``metacsp`` Java source tree -- ``java.awt.Rectangle`` is a JDK class)."""

    x: int
    y: int
    width: int
    height: int

    @property
    def min_x(self) -> int:
        return self.x

    @property
    def min_y(self) -> int:
        return self.y

    @property
    def max_x(self) -> int:
        return self.x + self.width

    @property
    def max_y(self) -> int:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def intersects(self, other: AwtRectangle) -> bool:
        """Port of ``java.awt.Rectangle.intersects(Rectangle)``."""
        tw, th = self.width, self.height
        rw, rh = other.width, other.height
        if rw <= 0 or rh <= 0 or tw <= 0 or th <= 0:
            return False
        tx, ty = self.x, self.y
        rx, ry = other.x, other.y
        rw += rx
        rh += ry
        tw += tx
        th += ty
        return (
            (rw < rx or rw > tx)
            and (rh < ry or rh > ty)
            and (tw < tx or tw > rx)
            and (th < ty or th > ry)
        )


class BoundingBox:
    """An axis-aligned box in 2D (or, if the Z bounds are given, 3D) space,
    described by the [min,max] interval of each axis's lower- and
    upper-bound coordinate (four or six :class:`Bounds`, one per corner
    coordinate range)."""

    def __init__(
        self,
        x_lb: Bounds,
        x_ub: Bounds,
        y_lb: Bounds,
        y_ub: Bounds,
        z_lb: Bounds | None = None,
        z_ub: Bounds | None = None,
    ) -> None:
        self._x_lb = x_lb
        self._x_ub = x_ub
        self._y_lb = y_lb
        self._y_ub = y_ub
        self._z_lb = z_lb
        self._z_ub = z_ub
        self._name = ""

    @property
    def x_lb(self) -> Bounds:
        return self._x_lb

    @property
    def x_ub(self) -> Bounds:
        return self._x_ub

    @property
    def y_lb(self) -> Bounds:
        return self._y_lb

    @property
    def y_ub(self) -> Bounds:
        return self._y_ub

    @property
    def z_lb(self) -> Bounds | None:
        return self._z_lb

    @property
    def z_ub(self) -> Bounds | None:
        return self._z_ub

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._name = name

    def get_min_rectangle(self) -> AwtRectangle:
        return AwtRectangle(
            int(self.x_lb.min),
            int(self.y_lb.min),
            int(self.x_ub.min - self.x_lb.min),
            int(self.y_ub.min - self.y_lb.min),
        )

    def get_max_rectangle(self) -> AwtRectangle:
        return AwtRectangle(
            int(self.x_lb.max),
            int(self.y_lb.max),
            int(self.x_ub.max - self.x_lb.max),
            int(self.y_ub.max - self.y_lb.max),
        )

    def get_almost_centre_rectangle(self) -> AwtRectangle:
        x = int(self.x_lb.min + _trunc_div(self.x_lb.max - self.x_lb.min, 2))
        y = int(self.y_lb.min + _trunc_div(self.y_lb.max - self.y_lb.min, 2))
        x2 = int(self.x_ub.min + _trunc_div(self.x_ub.max - self.x_ub.min, 2))
        y2 = int(self.y_ub.min + _trunc_div(self.y_ub.max - self.y_ub.min, 2))
        return AwtRectangle(x, y, x2 - x, y2 - y)

    def get_a_centre_point_solution(self) -> Point:
        r = self.get_almost_centre_rectangle()
        return Point(r.center_x, r.center_y)

    def get_almost_centre_rec_cuboid(self) -> RectangularCuboid:
        from metacsp.multi.spatial.block_algebra.rectangular_cuboid import RectangularCuboid

        assert self.z_lb is not None and self.z_ub is not None
        x = int(self.x_lb.min + _trunc_div(self.x_lb.max - self.x_lb.min, 2))
        y = int(self.y_lb.min + _trunc_div(self.y_lb.max - self.y_lb.min, 2))
        z = int(self.z_lb.min + _trunc_div(self.z_lb.max - self.z_lb.min, 2))
        x2 = int(self.x_ub.min + _trunc_div(self.x_ub.max - self.x_ub.min, 2))
        y2 = int(self.y_ub.min + _trunc_div(self.y_ub.max - self.y_ub.min, 2))
        z2 = int(self.z_ub.min + _trunc_div(self.z_ub.max - self.z_ub.min, 2))
        # Java's Point(int, int, int) call auto-widens the (int)-cast values
        # to the double fields of Point -- pass floats here so str(Point.x)
        # matches Java's Double.toString (e.g. "50.0", not "50").
        return RectangularCuboid(Point(float(x), float(y), float(z)), x2 - x, y2 - y, z2 - z)
