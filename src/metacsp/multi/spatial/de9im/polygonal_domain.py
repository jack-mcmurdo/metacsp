"""Port of multi/spatial/DE9IM/PolygonalDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from shapely.errors import GEOSException
from shapely.geometry import Point, Polygon

from metacsp.multi.spatial.de9im.geometric_shape_domain import GeometricShapeDomain
from metacsp.multi.spatial.spatial_domain import Coordinate

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["PolygonalDomain"]


class PolygonalDomain(GeometricShapeDomain):
    """Polygonal domains for :class:`GeometricShapeVariable`\\ s."""

    def __init__(self, v: Variable, coord: Sequence[Coordinate] | None = None) -> None:
        super().__init__(v, coord)
        self._update_geometry()

    def contains_point(self, point: Coordinate) -> bool:
        """True iff this :class:`PolygonalDomain` contains the given point."""
        return self.geometry.contains(Point(point))

    def _update_geometry(self) -> None:
        if self.coordinates is None:
            self.geom = Polygon()
        else:
            # Explicitly close the ring, as the Java original does (shapely
            # would also auto-close it, but this mirrors the source exactly).
            new_coords = list(self.coordinates) + [self.coordinates[0]]
            self.geom = Polygon(new_coords)
            if not self.geom.is_valid:
                try:
                    self.geom = self.geom.symmetric_difference(self.geom.boundary)
                except GEOSException:
                    self.logger.info("Trying to fix GeometricShapeVariable %s", self.variable.id)
                    self.geom = self.geom.buffer(0.1)
                    if not self.geom.is_valid:
                        self.logger.error("... giving up!")
                        raise
