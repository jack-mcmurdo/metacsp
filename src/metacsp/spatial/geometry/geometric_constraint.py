"""Port of spatial/geometry/GeometricConstraint.java."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from metacsp.framework.binary_constraint import BinaryConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["GeometricConstraint"]


class GeometricConstraint(BinaryConstraint):
    """A binary constraint over two Polygon-domain variables: disconnected (DC)
    or one inside the other (INSIDE)."""

    class Type(Enum):
        # Explicit 0-based values matching Java's ordinal() indexing into
        # TRANSITION_TABLE.
        DC = 0
        INSIDE = 1

    def __init__(self, type: Type) -> None:
        super().__init__()
        self.type = type

    def get_type(self) -> Type:
        return self.type

    @property
    def edge_label(self) -> str:
        return self.type.name

    def clone(self) -> GeometricConstraint | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False


Type = GeometricConstraint.Type

# Type.DC, Type.INSIDE
TRANSITION_TABLE: list[list[list[Type]]] = [
    [
        [Type.DC, Type.INSIDE],
        [Type.DC, Type.INSIDE],
    ],
    [
        [Type.DC],
        [Type.INSIDE],
    ],
]

GeometricConstraint.TRANSITION_TABLE = TRANSITION_TABLE
