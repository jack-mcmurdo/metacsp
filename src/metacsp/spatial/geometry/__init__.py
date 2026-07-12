"""Port of the ``spatial/geometry/`` package: 2D physics/collision geometry
and the RCC2/geometric constraint solvers built on top of it (M10)."""

from metacsp.spatial.geometry.collision_polygon_polygon import CollisionPolygonPolygon
from metacsp.spatial.geometry.geometric_constraint import GeometricConstraint
from metacsp.spatial.geometry.geometric_constraint_solver import GeometricConstraintSolver
from metacsp.spatial.geometry.impulse_math import ImpulseMath
from metacsp.spatial.geometry.manifold import Manifold
from metacsp.spatial.geometry.mat2 import Mat2
from metacsp.spatial.geometry.polygon import Polygon
from metacsp.spatial.geometry.pose import Pose
from metacsp.spatial.geometry.position import Position
from metacsp.spatial.geometry.quaternion import Quaternion
from metacsp.spatial.geometry.rcc2_constraint_solver import RCC2ConstraintSolver
from metacsp.spatial.geometry.sutherland_hodgman import SutherlandHodgman
from metacsp.spatial.geometry.vec2 import Vec2
from metacsp.spatial.geometry.vertex import Vertex

__all__ = [
    "CollisionPolygonPolygon",
    "GeometricConstraint",
    "GeometricConstraintSolver",
    "ImpulseMath",
    "Manifold",
    "Mat2",
    "Polygon",
    "Pose",
    "Position",
    "Quaternion",
    "RCC2ConstraintSolver",
    "SutherlandHodgman",
    "Vec2",
    "Vertex",
]
