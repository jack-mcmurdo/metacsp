"""Port of multi/spatial/DE9IM/GeometricShapeDomain.java."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Sequence

from shapely.geometry.base import BaseGeometry

from metacsp.multi.spatial.spatial_domain import Coordinate, SpatialDomain

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["GeometricShapeDomain"]


class GeometricShapeDomain(SpatialDomain, ABC):
    """Domain of a :class:`GeometricShapeVariable`: a point, line string, or
    polygon (see :class:`PointDomain`, :class:`LineStringDomain`,
    :class:`PolygonalDomain`).

    Geometric predicates are provided by shapely (GEOS), which methods
    provided by this class and its subclasses defer to (D4).
    """

    def __init__(self, v: Variable, coord: Sequence[Coordinate] | None = None) -> None:
        super().__init__(v, coord)
        self.geom: BaseGeometry | None = None

    @property
    def shape_type(self) -> type:
        """The class used to represent this domain."""
        return type(self)

    @property
    def geometry(self) -> BaseGeometry:
        """The shapely geometry used to represent this domain internally."""
        assert self.geom is not None
        return self.geom

    def __str__(self) -> str:
        assert self.geom is not None
        coord_info = (
            "no coordinates" if self.coordinates is None else f"{len(self.coordinates)} coordinates"
        )
        return f"{self.geom.geom_type} ({coord_info})"
