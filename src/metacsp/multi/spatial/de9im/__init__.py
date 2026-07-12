"""Port of the ``multi/spatial/DE9IM/`` package: Dimensionally Extended
nine-Intersection Model (DE-9IM) spatial relations between geometric shapes,
and their constraint solver (M12)."""

from metacsp.multi.spatial.de9im.de9im_relation import DE9IMRelation
from metacsp.multi.spatial.de9im.de9im_relation_solver import DE9IMRelationSolver
from metacsp.multi.spatial.de9im.geometric_shape_domain import GeometricShapeDomain
from metacsp.multi.spatial.de9im.geometric_shape_variable import GeometricShapeVariable
from metacsp.multi.spatial.de9im.line_string_domain import LineStringDomain
from metacsp.multi.spatial.de9im.point_domain import PointDomain
from metacsp.multi.spatial.de9im.polygonal_domain import PolygonalDomain

__all__ = [
    "DE9IMRelation",
    "DE9IMRelationSolver",
    "GeometricShapeDomain",
    "GeometricShapeVariable",
    "LineStringDomain",
    "PointDomain",
    "PolygonalDomain",
]
