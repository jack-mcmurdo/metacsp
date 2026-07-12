"""Port of multi/spatial/DE9IM/GeometricShapeVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from metacsp.framework.variable import Variable
from metacsp.multi.spatial.de9im.geometric_shape_domain import GeometricShapeDomain
from metacsp.multi.spatial.de9im.polygonal_domain import PolygonalDomain

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain

__all__ = ["GeometricShapeVariable"]


class GeometricShapeVariable(Variable):
    """A variable reasoned upon by the :class:`DE9IMRelationSolver`.

    Should be given a domain representing a point (:class:`PointDomain`),
    line string (:class:`LineStringDomain`), or polygon
    (:class:`PolygonalDomain`).
    """

    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._dom: GeometricShapeDomain = PolygonalDomain(self)

    @property
    def shape_type(self) -> type:
        """The class used to represent the domain of this variable."""
        return self._dom.shape_type

    def __lt__(self, other: Variable) -> bool:
        return self.id > other.id

    @property
    def domain(self) -> Domain:
        return self._dom

    @domain.setter
    def domain(self, d: Any) -> None:
        self._dom = d

    def __str__(self) -> str:
        return str(self.id)
