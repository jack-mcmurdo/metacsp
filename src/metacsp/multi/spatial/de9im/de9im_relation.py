"""Port of multi/spatial/DE9IM/DE9IMRelation.java.

Java uses reflection (``Geometry.class.getMethod(...)``) to dispatch on the
lowercased :class:`Type` name. Per C5, this is replaced by an explicit
lookup table mapping each :class:`Type` to the shapely predicate it calls.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from metacsp.framework.binary_constraint import BinaryConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.multi.spatial.de9im.geometric_shape_variable import GeometricShapeVariable

__all__ = ["DE9IMRelation"]

# Index of the (Boundary, Boundary) entry in a shapely/JTS DE-9IM relate()
# string ("II IB IE BI BB BE EI EB EE", flattened row-major).
_BB_INDEX = 4


class DE9IMRelation(BinaryConstraint):
    """Spatial relations between geometric shapes (variables of type
    :class:`GeometricShapeVariable`): points, line strings, or polygons.

    These relations constitute the Dimensionally Extended nine-Intersection
    Model (DE-9IM) (Clementini et al., 1993;
    https://en.wikipedia.org/wiki/DE-9IM). If the shapes are all polygons,
    a Jointly Exclusive and Pairwise Disjoint (JEPD) subset of these
    relations is equivalent to RCC8 (Cohn et al., 2007).
    """

    class Type(Enum):
        """The 10 meaningful relations in DE-9IM. The subset
        ``{Contains, Within, Covers, CoveredBy, Disjoint, Overlaps, Touches,
        Equals}`` is JEPD and equivalent to RCC8 (Cohn et al., 2007)."""

        Contains = "Contains"
        Within = "Within"
        Covers = "Covers"
        CoveredBy = "CoveredBy"
        Intersects = "Intersects"
        Disjoint = "Disjoint"
        Crosses = "Crosses"
        Overlaps = "Overlaps"
        Touches = "Touches"
        Equals = "Equals"

    # Explicit dispatch table (C5) mapping each Type to the shapely geometry
    # predicate method it corresponds to (replaces Java's reflective lookup
    # of ``Geometry.<lowercased-name>(Geometry)``).
    _PREDICATE_METHODS: dict[Type, str] = {
        Type.Contains: "contains",
        Type.Within: "within",
        Type.Covers: "covers",
        Type.CoveredBy: "covered_by",
        Type.Intersects: "intersects",
        Type.Disjoint: "disjoint",
        Type.Crosses: "crosses",
        Type.Overlaps: "overlaps",
        Type.Touches: "touches",
        Type.Equals: "equals",
    }

    # Subset for polygons, equivalent to RCC8 (Cohn, 2007).
    _RCC8_TYPES: frozenset[Type] = frozenset(
        {
            Type.Contains,
            Type.Within,
            Type.Covers,
            Type.CoveredBy,
            Type.Disjoint,
            Type.Overlaps,
            Type.Touches,
            Type.Equals,
        }
    )

    def __init__(self, *types: Type) -> None:
        super().__init__()
        self._types: tuple[DE9IMRelation.Type, ...] = types

    def is_relation(self, relation_type: DE9IMRelation.Type) -> bool:
        """Assess whether this relation is of a given :class:`Type`."""
        return any(t == relation_type for t in self._types)

    @property
    def types(self) -> tuple[DE9IMRelation.Type, ...]:
        """The types of this DE-9IM relation."""
        return self._types

    @property
    def edge_label(self) -> str:
        return "[" + ", ".join(t.name for t in self._types) + "]"

    def clone(self) -> DE9IMRelation:
        ret = DE9IMRelation(*self._types)
        ret.from_ = self.from_
        ret.to = self.to
        return ret

    def is_equivalent(self, c: Constraint) -> bool:
        if not isinstance(c, DE9IMRelation):
            return False
        this_types = set(self.types)
        that_types = set(c.types)
        return len(this_types) == len(that_types) and this_types.issuperset(that_types)

    # __str__ is inherited from BinaryConstraint unchanged (Java does not
    # override toString() for DE9IMRelation, only getEdgeLabel()).

    # --- static/class-level relation queries ---

    @staticmethod
    def get_relations(
        gv1: GeometricShapeVariable, gv2: GeometricShapeVariable
    ) -> list[DE9IMRelation.Type]:
        """Get the DE-9IM relation(s) existing between two
        :class:`GeometricShapeVariable`\\ s."""
        return DE9IMRelation._get_relations(gv1, gv2, False)

    @staticmethod
    def get_rcc8_relations(
        gv1: GeometricShapeVariable, gv2: GeometricShapeVariable
    ) -> list[DE9IMRelation.Type]:
        """Get the RCC8 relation(s) existing between two
        :class:`GeometricShapeVariable`\\ s."""
        return DE9IMRelation._get_relations(gv1, gv2, True)

    @staticmethod
    def is_relation_between(
        gv1: GeometricShapeVariable, gv2: GeometricShapeVariable, t: DE9IMRelation.Type
    ) -> bool:
        """Check if the spatial relation between two
        :class:`GeometricShapeVariable`\\ s is of a given type.

        Java overloads this as a second, static ``isRelation``; renamed here
        (Python has no method overloading) to avoid clashing with the
        instance method :meth:`is_relation`.
        """
        g1 = gv1.domain.geometry  # type: ignore[union-attr]
        g2 = gv2.domain.geometry  # type: ignore[union-attr]
        method = DE9IMRelation._PREDICATE_METHODS[t]
        return bool(getattr(g1, method)(g2))

    @staticmethod
    def is_rcc8_relation(t: DE9IMRelation.Type) -> bool:
        """Find out whether a :class:`Type` belongs to the RCC8 subset."""
        return t in DE9IMRelation._RCC8_TYPES

    @staticmethod
    def _get_relations(
        gv1: GeometricShapeVariable, gv2: GeometricShapeVariable, rcc8_relations: bool
    ) -> list[DE9IMRelation.Type]:
        ret: list[DE9IMRelation.Type] = []
        g1 = gv1.domain.geometry  # type: ignore[union-attr]
        g2 = gv2.domain.geometry  # type: ignore[union-attr]

        for t in DE9IMRelation.Type:
            if rcc8_relations and not DE9IMRelation.is_rcc8_relation(t):
                continue
            method = DE9IMRelation._PREDICATE_METHODS[t]
            if bool(getattr(g1, method)(g2)):
                skip = False
                if t is DE9IMRelation.Type.Covers or t is DE9IMRelation.Type.CoveredBy:
                    mat = g1.relate(g2)
                    if mat[_BB_INDEX] == "F":
                        skip = True
                elif t is DE9IMRelation.Type.Contains or t is DE9IMRelation.Type.Within:
                    mat = g1.relate(g2)
                    if mat[_BB_INDEX] == "1":
                        skip = True
                if not skip:
                    ret.append(t)
        if rcc8_relations and DE9IMRelation.Type.Equals in ret:
            return [DE9IMRelation.Type.Equals]
        return ret
