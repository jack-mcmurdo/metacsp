"""Port of multi/spatial/DE9IM/LineStringDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from shapely.geometry import LineString

from metacsp.multi.spatial.de9im.geometric_shape_domain import GeometricShapeDomain
from metacsp.multi.spatial.spatial_domain import Coordinate

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["LineStringDomain"]


class LineStringDomain(GeometricShapeDomain):
    """Line string domains for :class:`GeometricShapeVariable`\\ s."""

    def __init__(self, v: Variable, coord: Sequence[Coordinate] | None = None) -> None:
        super().__init__(v, coord)
        self._update_geometry()

    @property
    def geometry_coordinates(self) -> list[Coordinate]:
        """The coordinates of this domain's geometry.

        Fixes the upstream ``getCoordiantes()`` typo (C2); renamed from the
        obvious ``coordinates`` to avoid shadowing :attr:`coordinates`, which
        holds the raw coordinates this domain was constructed with.
        """
        return list(self.geometry.coords)

    def _update_geometry(self) -> None:
        if self.coordinates is None:
            self.geom = LineString()
        else:
            self.geom = LineString(self.coordinates)
