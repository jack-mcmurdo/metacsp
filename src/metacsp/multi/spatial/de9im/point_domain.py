"""Port of multi/spatial/DE9IM/PointDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shapely.geometry import Point

from metacsp.multi.spatial.de9im.geometric_shape_domain import GeometricShapeDomain
from metacsp.multi.spatial.spatial_domain import Coordinate

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["PointDomain"]


class PointDomain(GeometricShapeDomain):
    """Point domains for :class:`GeometricShapeVariable`\\ s."""

    def __init__(self, v: Variable, coord: Coordinate | None = None) -> None:
        super().__init__(v, [coord] if coord is not None else None)
        self._update_geometry()

    def _update_geometry(self) -> None:
        if self.coordinates is None:
            # Java calls `new Coordinate(null)`, which NPEs at runtime if ever
            # exercised (this branch is otherwise unreachable via the public
            # API); an empty Point is the well-defined equivalent, consistent
            # with the sibling domains' no-coordinate behavior.
            self.geom = Point()
        else:
            self.geom = Point(self.coordinates[0])
