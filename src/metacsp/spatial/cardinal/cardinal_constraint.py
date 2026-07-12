"""Port of spatial/cardinal/CardinalConstraint.java.

The Java class has no explicit constructor (a default no-arg constructor is
generated), and no getter/setter for ``types`` -- ``getEdgeLabel``, ``clone``
and ``isEquivalent`` are all left as unfinished "TODO Auto-generated method
stub" bodies. This is ported as-is, stub for stub.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from metacsp.framework.binary_constraint import BinaryConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["CardinalConstraint"]


class CardinalConstraint(BinaryConstraint):
    """A binary constraint stating the cardinal direction (North, East, ...)
    of one region relative to another."""

    class Type(Enum):
        North = 0
        West = 1
        South = 2
        East = 3
        NorthEast = 4
        NorthWest = 5
        SouthEast = 6
        SouthWest = 7
        EQUAL = 8
        NO = 9

    # Has to be completed (Java comment, kept verbatim).
    CARDINAL_RELATION_TO_METRIC_ORIENTATION: list[float] = [
        -1.57,  # North
        0.0,  # West
        1.57,  # south
        3.14,  # East
        0.0,  # NorthEast
        0.0,  # NorthWest
        0.0,  # SouthEast
        0.0,  # SouthWest
        0.0,  # Equal
        0.0,  # NO
    ]

    def __init__(self) -> None:
        super().__init__()
        self.types: list[CardinalConstraint.Type] | None = None

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> CardinalConstraint | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False
