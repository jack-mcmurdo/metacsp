"""Port of the ``multi/spatial/rectangleAlgebra/`` package: Rectangle
Algebra -- axis-parallel rectangles reasoned about as a pair of Allen
intervals (one per axis) -- and its constraint solver (M13)."""

from metacsp.multi.spatial.rectangle_algebra.bounding_box import BoundingBox
from metacsp.multi.spatial.rectangle_algebra.point import Point
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint_solver import (
    RectangleConstraintSolver,
)
from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)

__all__ = [
    "BoundingBox",
    "Point",
    "RectangleConstraint",
    "RectangleConstraintSolver",
    "RectangularRegion",
    "UnaryRectangleConstraint",
]
