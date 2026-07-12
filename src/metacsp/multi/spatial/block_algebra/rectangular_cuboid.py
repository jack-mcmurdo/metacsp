"""Port of multi/spatial/blockAlgebra/RectangularCuboid.java."""

from __future__ import annotations

from metacsp.multi.spatial.rectangle_algebra.point import Point

__all__ = ["RectangularCuboid"]


class RectangularCuboid:
    """An axis-parallel cuboid: a corner :class:`Point` plus length, width,
    and height."""

    def __init__(self, point: Point, length: int, width: int, height: int) -> None:
        self.point = point
        self.length = length
        self.width = width
        self.height = height

    def __str__(self) -> str:
        # Reproduces Java's exact (typo'd: "lenght", and missing "width: "
        # label) printed format verbatim -- this string is directly
        # observed by the ported TestBlockAlgebraConstraintSolverSimple
        # example, so its exact text is part of the oracle's observable
        # behavior.
        return (
            "["
            + "x: "
            + str(self.point.x)
            + ", "
            + "y: "
            + str(self.point.y)
            + ", "
            + "z: "
            + str(self.point.z)
            + ", "
            + "lenght: "
            + str(self.length)
            + ", "
            + ": "
            + str(self.width)
            + ", "
            + "height: "
            + str(self.height)
            + "]"
        )
