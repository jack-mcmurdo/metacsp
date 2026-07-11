"""Port of time/qualitative/QualitativeAllenIntervalConstraint.java.

There are 13 types of Allen interval constraints (see [Allen 1984]).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Sequence

from metacsp.framework.binary_constraint import BinaryConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint

__all__ = ["QualitativeAllenIntervalConstraint"]


class QualitativeAllenIntervalConstraint(BinaryConstraint):
    """A disjunction of basic Allen interval relations."""

    class Type(Enum):
        Before = 0
        Meets = 1
        Overlaps = 2
        FinishedBy = 3
        Contains = 4
        StartedBy = 5
        Equals = 6
        Starts = 7
        During = 8
        Finishes = 9
        OverlappedBy = 10
        MetBy = 11
        After = 12

    def __init__(self, *types: Type) -> None:
        super().__init__()
        self.types: list[QualitativeAllenIntervalConstraint.Type] = list(types)

    def contains_type(self, type_: Type) -> bool:
        return type_ in self.types

    def clone(self) -> QualitativeAllenIntervalConstraint:
        ret = QualitativeAllenIntervalConstraint()
        ret.types = self.types
        return ret

    @property
    def edge_label(self) -> str:
        if not self.types:
            return ""
        if len(self.types) == 1:
            return self.types[0].name
        return "{" + " v ".join(t.name for t in self.types) + "}"

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    # --- Type ordinal / relation utilities ---

    @staticmethod
    def get_inverse_relation(t: Type | Sequence[Type]):
        if isinstance(t, QualitativeAllenIntervalConstraint.Type):
            return _INVERSE[t]
        return [_INVERSE[one] for one in t]

    @staticmethod
    def lookup_type_by_int(i: int) -> Type:
        return QualitativeAllenIntervalConstraint.Type(i)

    @staticmethod
    def _dimension_of_basic_rel(t: Type) -> int:
        Type = QualitativeAllenIntervalConstraint.Type
        if t in (Type.Before, Type.After):
            return 2
        if t in (Type.Meets, Type.MetBy):
            return 1
        if t in (Type.Overlaps, Type.OverlappedBy):
            return 2
        if t in (Type.Finishes, Type.FinishedBy):
            return 1
        if t in (Type.Starts, Type.StartedBy):
            return 1
        if t in (Type.During, Type.Contains):
            return 2
        return 0

    @staticmethod
    def get_dimension(*types: Type) -> int:
        if not types:
            return -1
        return max(QualitativeAllenIntervalConstraint._dimension_of_basic_rel(t) for t in types)

    @staticmethod
    def _canonical_allen_representation(t: Type) -> tuple[int, int]:
        Type = QualitativeAllenIntervalConstraint.Type
        return {
            Type.Before: (0, 0),
            Type.Meets: (0, 1),
            Type.Overlaps: (0, 2),
            Type.Finishes: (2, 3),
            Type.Starts: (1, 2),
            Type.During: (2, 2),
            Type.After: (4, 4),
            Type.MetBy: (3, 4),
            Type.OverlappedBy: (2, 4),
            Type.FinishedBy: (0, 3),
            Type.StartedBy: (1, 4),
            Type.Contains: (0, 4),
            Type.Equals: (1, 3),
        }[t]

    @staticmethod
    def _allen_rel_by_coordinate(x: int, y: int) -> Type | None:
        Type = QualitativeAllenIntervalConstraint.Type
        return {
            (0, 0): Type.Before,
            (0, 1): Type.Meets,
            (0, 2): Type.Overlaps,
            (2, 3): Type.Finishes,
            (1, 2): Type.Starts,
            (2, 2): Type.During,
            (4, 4): Type.After,
            (3, 4): Type.MetBy,
            (2, 4): Type.OverlappedBy,
            (0, 3): Type.FinishedBy,
            (1, 4): Type.StartedBy,
            (0, 4): Type.Contains,
            (1, 3): Type.Equals,
        }.get((x, y))

    @staticmethod
    def get_allen_convex_closure(*types: Type) -> list[Type]:
        """Convex closure of Allen Interval based on the canonical
        representation of interval atomic relations [Ligozat, 1996], and on
        "Geometrical Interpretation of Maximal Tractable Interval
        Subalgebras" [F. Launay, D. Mitra, 06]."""
        coords = [
            QualitativeAllenIntervalConstraint._canonical_allen_representation(t) for t in types
        ]
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        low_x, high_x = min(xs), max(xs)
        low_y, high_y = min(ys), max(ys)
        convex: list[QualitativeAllenIntervalConstraint.Type] = []
        for x in range(low_x, high_x + 1):
            for y in range(low_y, high_y + 1):
                rel = QualitativeAllenIntervalConstraint._allen_rel_by_coordinate(x, y)
                if rel is not None:
                    convex.append(rel)
        return convex

    def is_preconvex(self, *types: Type) -> bool:
        """A relation R is pre-convex (weakly preconvex) iff
        dim(I(R)\\R) < dim(R)."""
        convex_closure = QualitativeAllenIntervalConstraint.get_allen_convex_closure(*types)
        convex_minus_r = [t for t in convex_closure if t not in types]
        return QualitativeAllenIntervalConstraint.get_dimension(
            *convex_minus_r
        ) < QualitativeAllenIntervalConstraint.get_dimension(*types)


Type = QualitativeAllenIntervalConstraint.Type

_INVERSE: dict[Type, Type] = {
    Type.Before: Type.After,
    Type.After: Type.Before,
    Type.Meets: Type.MetBy,
    Type.MetBy: Type.Meets,
    Type.Overlaps: Type.OverlappedBy,
    Type.OverlappedBy: Type.Overlaps,
    Type.FinishedBy: Type.Finishes,
    Type.Finishes: Type.FinishedBy,
    Type.StartedBy: Type.Starts,
    Type.Starts: Type.StartedBy,
    Type.Contains: Type.During,
    Type.During: Type.Contains,
    Type.Equals: Type.Equals,
}

# The composition table used by path consistency: transition_table[t1][t2] is
# the disjunction of basic relations satisfying R1(a,b) and R2(b,c) => (a,c).
TRANSITION_TABLE: list[list[list[Type]]] = [
    [
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before, Type.Meets, Type.Overlaps, Type.Starts, Type.During],
        [Type.Before, Type.Meets, Type.Overlaps, Type.Starts, Type.During],
        [Type.Before, Type.Meets, Type.Overlaps, Type.Starts, Type.During],
        [Type.Before, Type.Meets, Type.Overlaps, Type.Starts, Type.During],
        [
            Type.Before,
            Type.Meets,
            Type.Overlaps,
            Type.Starts,
            Type.During,
            Type.Finishes,
            Type.Equals,
            Type.FinishedBy,
            Type.Contains,
            Type.StartedBy,
            Type.OverlappedBy,
            Type.MetBy,
            Type.After,
        ],
    ],
    [
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Before],
        [Type.Meets],
        [Type.Meets],
        [Type.Meets],
        [Type.Overlaps, Type.Starts, Type.During],
        [Type.Overlaps, Type.Starts, Type.During],
        [Type.Overlaps, Type.Starts, Type.During],
        [Type.Finishes, Type.Equals, Type.FinishedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy, Type.MetBy, Type.After],
    ],
    [
        [Type.Before],
        [Type.Before],
        [Type.Before, Type.Meets, Type.Overlaps],
        [Type.Before, Type.Meets, Type.Overlaps],
        [Type.Before, Type.Meets, Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Overlaps],
        [Type.Overlaps],
        [Type.Overlaps, Type.Starts, Type.During],
        [Type.Overlaps, Type.Starts, Type.During],
        [
            Type.Overlaps,
            Type.Starts,
            Type.During,
            Type.Finishes,
            Type.Equals,
            Type.FinishedBy,
            Type.Contains,
            Type.StartedBy,
            Type.OverlappedBy,
        ],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy, Type.MetBy, Type.After],
    ],
    [
        [Type.Before],
        [Type.Meets],
        [Type.Overlaps],
        [Type.FinishedBy],
        [Type.Contains],
        [Type.Contains],
        [Type.FinishedBy],
        [Type.Overlaps],
        [Type.Overlaps, Type.Starts, Type.During],
        [Type.Finishes, Type.Equals, Type.FinishedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy, Type.MetBy, Type.After],
    ],
    [
        [Type.Before, Type.Meets, Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Contains],
        [Type.Contains],
        [Type.Contains],
        [Type.Contains],
        [Type.Overlaps, Type.FinishedBy, Type.Contains],
        [
            Type.Overlaps,
            Type.Starts,
            Type.During,
            Type.Finishes,
            Type.Equals,
            Type.FinishedBy,
            Type.Contains,
            Type.StartedBy,
            Type.OverlappedBy,
        ],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy, Type.MetBy, Type.After],
    ],
    [
        [Type.Before, Type.Meets, Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Contains],
        [Type.Contains],
        [Type.StartedBy],
        [Type.StartedBy],
        [Type.Starts, Type.Equals, Type.StartedBy],
        [Type.During, Type.Finishes, Type.OverlappedBy],
        [Type.OverlappedBy],
        [Type.OverlappedBy],
        [Type.MetBy],
        [Type.After],
    ],
    [
        [Type.Before],
        [Type.Meets],
        [Type.Overlaps],
        [Type.FinishedBy],
        [Type.Contains],
        [Type.StartedBy],
        [Type.Equals],
        [Type.Starts],
        [Type.During],
        [Type.Finishes],
        [Type.OverlappedBy],
        [Type.MetBy],
        [Type.After],
    ],
    [
        [Type.Before],
        [Type.Before],
        [Type.Before, Type.Meets, Type.Overlaps],
        [Type.Before, Type.Meets, Type.Overlaps],
        [Type.Before, Type.Meets, Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Starts, Type.Equals, Type.StartedBy],
        [Type.Starts],
        [Type.Starts],
        [Type.During],
        [Type.During],
        [Type.During, Type.Finishes, Type.OverlappedBy],
        [Type.MetBy],
        [Type.After],
    ],
    [
        [Type.Before],
        [Type.Before],
        [Type.Before, Type.Meets, Type.Overlaps, Type.Starts, Type.During],
        [Type.Before, Type.Meets, Type.Overlaps, Type.Starts, Type.During],
        [
            Type.Before,
            Type.Meets,
            Type.Overlaps,
            Type.Starts,
            Type.During,
            Type.Finishes,
            Type.Equals,
            Type.FinishedBy,
            Type.Contains,
            Type.StartedBy,
            Type.OverlappedBy,
            Type.MetBy,
            Type.After,
        ],
        [Type.During, Type.Finishes, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.During],
        [Type.During],
        [Type.During],
        [Type.During],
        [Type.During, Type.Finishes, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.After],
        [Type.After],
    ],
    [
        [Type.Before],
        [Type.Meets],
        [Type.Overlaps, Type.Starts, Type.During],
        [Type.Finishes, Type.Equals, Type.FinishedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.Finishes],
        [Type.During],
        [Type.During],
        [Type.Finishes],
        [Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.After],
        [Type.After],
    ],
    [
        [Type.Before, Type.Meets, Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Overlaps, Type.FinishedBy, Type.Contains],
        [
            Type.Overlaps,
            Type.Starts,
            Type.During,
            Type.Finishes,
            Type.Equals,
            Type.FinishedBy,
            Type.Contains,
            Type.StartedBy,
            Type.OverlappedBy,
        ],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy],
        [Type.Contains, Type.StartedBy, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.OverlappedBy],
        [Type.During, Type.Finishes, Type.OverlappedBy],
        [Type.During, Type.Finishes, Type.OverlappedBy],
        [Type.OverlappedBy],
        [Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.After],
        [Type.After],
    ],
    [
        [Type.Before, Type.Meets, Type.Overlaps, Type.FinishedBy, Type.Contains],
        [Type.Starts, Type.Equals, Type.StartedBy],
        [Type.During, Type.Finishes, Type.OverlappedBy],
        [Type.MetBy],
        [Type.After],
        [Type.After],
        [Type.MetBy],
        [Type.During, Type.Finishes, Type.OverlappedBy],
        [Type.During, Type.Finishes, Type.OverlappedBy],
        [Type.MetBy],
        [Type.After],
        [Type.After],
        [Type.After],
    ],
    [
        [
            Type.Before,
            Type.Meets,
            Type.Overlaps,
            Type.Starts,
            Type.During,
            Type.Finishes,
            Type.Equals,
            Type.FinishedBy,
            Type.Contains,
            Type.StartedBy,
            Type.OverlappedBy,
            Type.MetBy,
            Type.After,
        ],
        [Type.During, Type.Finishes, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.During, Type.Finishes, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.After],
        [Type.After],
        [Type.After],
        [Type.After],
        [Type.During, Type.Finishes, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.During, Type.Finishes, Type.OverlappedBy, Type.MetBy, Type.After],
        [Type.After],
        [Type.After],
        [Type.After],
        [Type.After],
    ],
]

# topological_closure[t] is the disjunction of relations "at least as tight
# as" t in the topological ordering used by path consistency.
TOPOLOGICAL_CLOSURE: list[list[Type]] = [
    [Type.Before, Type.Meets],
    [Type.Meets],
    [Type.Meets, Type.Overlaps, Type.FinishedBy, Type.Starts, Type.Equals],
    [Type.FinishedBy, Type.Equals],
    [Type.Contains, Type.StartedBy, Type.FinishedBy, Type.Equals],
    [Type.StartedBy, Type.Equals],
    [Type.Equals],
    [Type.Starts, Type.Equals],
    [Type.During, Type.Starts, Type.Finishes, Type.Equals],
    [Type.Finishes, Type.Equals],
    [Type.MetBy, Type.OverlappedBy, Type.Finishes, Type.StartedBy, Type.Equals],
    [Type.MetBy],
    [Type.MetBy, Type.After],
]

# Re-exposed as class attributes to match Java's `QualitativeAllenIntervalConstraint
# .transitionTable`/`.topologicalClosure` call sites (C2: Java static fields stay
# class attributes).
QualitativeAllenIntervalConstraint.TRANSITION_TABLE = TRANSITION_TABLE
QualitativeAllenIntervalConstraint.TOPOLOGICAL_CLOSURE = TOPOLOGICAL_CLOSURE
