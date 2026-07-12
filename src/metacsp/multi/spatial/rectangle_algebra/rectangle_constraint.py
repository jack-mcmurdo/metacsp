"""Port of multi/spatial/rectangleAlgebra/RectangleConstraint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from metacsp.framework.multi.multi_binary_constraint import MultiBinaryConstraint
from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.spatial.cardinal.cardinal_constraint import CardinalConstraint
from metacsp.spatial.rcc.rcc_constraint import RCCConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion

__all__ = ["RectangleConstraint"]

_Type = AllenIntervalConstraint.Type


def _ordinal(t: AllenIntervalConstraint.Type) -> int:
    """The 0-based declaration-order index of an AllenIntervalConstraint.Type,
    matching Java's ``Enum.ordinal()`` (the ``Type`` enum's ``value`` is
    assigned sequentially from 1 in declaration order -- see
    ``allen_interval_constraint.py``)."""
    return t.value - 1


def _java_array_str(types: list[AllenIntervalConstraint.Type]) -> str:
    """Mimics Java's ``Arrays.toString(Object[])``."""
    return "[" + ", ".join(t.name for t in types) + "]"


# Short local aliases, used only to keep the two big table literals below
# readable -- not part of the ported Java API.
_DC, _EC, _PO = RCCConstraint.Type.DC, RCCConstraint.Type.EC, RCCConstraint.Type.PO
_TPP, _NTPP = RCCConstraint.Type.TPP, RCCConstraint.Type.NTPP
_TPPI, _NTPPI, _EQ = RCCConstraint.Type.TPPI, RCCConstraint.Type.NTPPI, RCCConstraint.Type.EQ
_West, _South = CardinalConstraint.Type.West, CardinalConstraint.Type.South
_East, _North, _NO = (
    CardinalConstraint.Type.East,
    CardinalConstraint.Type.North,
    CardinalConstraint.Type.NO,
)


def _make_cardinal_by_2dim(
    t1: CardinalConstraint.Type, t2: CardinalConstraint.Type
) -> CardinalConstraint.Type | None:
    if t1 == _NO and t2 == _NO:
        return _NO
    if t1 == _NO and t2 != _NO:
        return t2
    if t1 != _NO and t2 == _NO:
        return t1
    if t1 == _East and t2 == _North:
        return CardinalConstraint.Type.NorthEast
    if t1 == _West and t2 == _North:
        return CardinalConstraint.Type.NorthWest
    if t1 == _East and t2 == _South:
        return CardinalConstraint.Type.SouthEast
    if t1 == _West and t2 == _South:
        return CardinalConstraint.Type.SouthWest
    return None


class RectangleConstraint(MultiBinaryConstraint):
    """A binary constraint over two :class:`RectangularRegion` variables: a
    pair of AllenIntervalConstraints, one per axis (X and Y) -- the core
    relation of Rectangle Algebra."""

    # 13x13 RCC-8 composition table, indexed by [ordinal(x-axis
    # type)][ordinal(y-axis type)] where both types are one of the 13 basic
    # AllenIntervalConstraint.Type relations (Before, Meets, Overlaps,
    # FinishedBy, Contains, StartedBy, Equals, Starts, During, Finishes,
    # OverlappedBy, After, MetBy -- this is the declaration/ordinal order).
    # Fixes the upstream "Reactangle" typo in the field name. Transcribed
    # verbatim from RectangleConstraint.java; that source's row comments for
    # indices 11/12 read "METBY"/"AFTER" (the reverse of the true ordinal
    # order, where After=11 and MetBy=12) but this is harmless -- rows 0/12
    # (all DC) and rows 1/11 (Meets/MetBy) are identical to each other in
    # the original table either way, so indexing by true ordinal reproduces
    # Java's exact runtime behavior.
    RECTANGLE_TO_RCC: ClassVar[list[list[RCCConstraint.Type]]] = [
        [_DC] * 13,  # Before
        [_DC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _DC],  # Meets
        [_DC, _EC, _PO, _PO, _PO, _PO, _PO, _PO, _PO, _PO, _PO, _EC, _DC],  # Overlaps
        [_DC, _EC, _PO, _TPPI, _PO, _PO, _TPPI, _PO, _PO, _PO, _PO, _EC, _DC],  # FinishedBy
        [_DC, _EC, _PO, _PO, _NTPPI, _PO, _TPPI, _PO, _PO, _PO, _PO, _DC, _EC],  # Contains
        [_DC, _EC, _PO, _PO, _PO, _TPPI, _TPPI, _PO, _TPP, _PO, _PO, _EC, _DC],  # StartedBy
        [_EC, _DC, _PO, _TPPI, _TPPI, _TPPI, _EQ, _TPP, _TPP, _TPP, _PO, _EC, _DC],  # Equals
        [_DC, _EC, _PO, _PO, _PO, _PO, _TPP, _TPP, _TPP, _TPP, _PO, _EC, _DC],  # Starts
        [_DC, _EC, _PO, _PO, _PO, _TPP, _TPP, _TPP, _NTPP, _TPP, _PO, _EC, _DC],  # During
        [_DC, _EC, _PO, _PO, _PO, _PO, _TPP, _TPP, _TPP, _TPP, _PO, _EC, _DC],  # Finishes
        [_DC, _EC, _PO, _PO, _PO, _PO, _PO, _PO, _PO, _PO, _PO, _DC, _EC],  # OverlappedBy
        [_DC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _EC, _DC],  # MetBy (src: AFTER)
        [_DC] * 13,  # After (source comment: METBY)
    ]

    RECTANGLE_TO_CARDINAL_X: ClassVar[list[CardinalConstraint.Type]] = [
        _West,  # Before
        _West,  # Meets
        _West,  # Overlaps
        _NO,  # FinishedBy
        _NO,  # Contains
        _NO,  # StartedBy
        _NO,  # Equals
        _NO,  # Starts
        _NO,  # During
        _NO,  # Finishes
        _East,  # OverlappedBy
        _East,  # MetBy
        _East,  # After
    ]

    RECTANGLE_TO_CARDINAL_Y: ClassVar[list[CardinalConstraint.Type]] = [
        _South,  # Before
        _South,  # Meets
        _South,  # Overlaps
        _NO,  # FinishedBy
        _NO,  # Contains
        _NO,  # StartedBy
        _NO,  # Equals
        _NO,  # Starts
        _NO,  # During
        _NO,  # Finishes
        _North,  # OverlappedBy
        _North,  # MetBy
        _North,  # After
    ]

    def __init__(
        self, x_constraint: AllenIntervalConstraint, y_constraint: AllenIntervalConstraint
    ) -> None:
        super().__init__()
        self.x_constraint = x_constraint
        self.y_constraint = y_constraint
        self._type: list[list[AllenIntervalConstraint.Type]] = [
            x_constraint.types,
            y_constraint.types,
        ]

    @property
    def type(self) -> list[list[AllenIntervalConstraint.Type]]:
        """Java's ``getType()`` (singular, despite returning the whole
        per-axis type-lists array) -- the property name mirrors that getter
        exactly, per C2."""
        return self._type

    @staticmethod
    def get_rcc_constraint(
        x: AllenIntervalConstraint.Type, y: AllenIntervalConstraint.Type
    ) -> RCCConstraint.Type:
        return RectangleConstraint.RECTANGLE_TO_RCC[_ordinal(x)][_ordinal(y)]

    @property
    def internal_allen_interval_constraints(self) -> list[AllenIntervalConstraint]:
        return [self.x_constraint, self.y_constraint]

    @staticmethod
    def get_cardinal_constraint(c: RectangleConstraint) -> CardinalConstraint.Type | None:
        if c.type[0][0] == _Type.Equals and c.type[1][0] == _Type.Equals:
            return CardinalConstraint.Type.EQUAL
        return _make_cardinal_by_2dim(
            RectangleConstraint.RECTANGLE_TO_CARDINAL_X[_ordinal(c.type[0][0])],
            RectangleConstraint.RECTANGLE_TO_CARDINAL_Y[_ordinal(c.type[1][0])],
        )

    def create_internal_constraints_from_to(
        self, from_: Variable, to: Variable
    ) -> list[Constraint]:
        from_r = cast("RectangularRegion", from_)
        to_r = cast("RectangularRegion", to)
        self.x_constraint.from_ = from_r.internal_variables[0]
        self.x_constraint.to = to_r.internal_variables[0]
        self.y_constraint.from_ = from_r.internal_variables[1]
        self.y_constraint.to = to_r.internal_variables[1]
        # xConstraint should not be processed by the Y solver
        self.x_constraint.skip_solver(cast(MultiVariable, from_r).internal_constraint_solvers[1])
        # yConstraint should not be processed by the X solver
        self.y_constraint.skip_solver(cast(MultiVariable, from_r).internal_constraint_solvers[0])
        return [self.x_constraint, self.y_constraint]

    def is_equivalent(self, c: Constraint) -> bool:
        rc = cast(RectangleConstraint, c)
        internal = rc.internal_constraints
        assert internal is not None
        return self.x_constraint.is_equivalent(internal[0]) and self.y_constraint.is_equivalent(
            internal[1]
        )

    def clone(self) -> RectangleConstraint:
        return RectangleConstraint(self.x_constraint, self.y_constraint)

    def __str__(self) -> str:
        ret = f"[{self.from_} ---"
        ret += f"({_java_array_str(self.type[0])}, {_java_array_str(self.type[1])})"
        ret += f"--> ({self.to}]"
        return ret

    @property
    def edge_label(self) -> str:
        return f"({_java_array_str(self.type[0])}, {_java_array_str(self.type[1])})"
