"""Port of multi/spatial/SpatialDomain.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Sequence

from metacsp.framework.domain import Domain

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["SpatialDomain"]

# A JTS Coordinate maps to a plain (x, y) tuple (D4).
Coordinate = tuple[float, float]


class SpatialDomain(Domain, ABC):
    """Common base for domains that are defined by a sequence of coordinates
    (points, line strings, polygons -- see :class:`GeometricShapeDomain`)."""

    def __init__(self, v: Variable, coord: Sequence[Coordinate] | None = None) -> None:
        super().__init__(v)
        # Java distinguishes the no-coordinate constructor (coordinates = null)
        # from being explicitly given a zero-length array; the latter is never
        # exercised in this codebase, so both collapse to None here.
        self.coordinates: list[Coordinate] | None = list(coord) if coord else None

    @property
    def is_instantiated(self) -> bool:
        return self.coordinates is not None and len(self.coordinates) > 0

    @abstractmethod
    def _update_geometry(self) -> None: ...

    def set_coordinates(self, *coord: Coordinate) -> None:
        """Set the coordinates of this domain.

        Mirrors the Java setter exactly: it does *not* refresh the derived
        geometry -- callers must invoke the (protected) geometry update
        themselves, as in the Java original.
        """
        self.coordinates = list(coord) if coord else None

    def compare_to(self, other: object) -> int:
        return 0
