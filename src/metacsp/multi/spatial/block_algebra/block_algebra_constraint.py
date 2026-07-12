"""Port of multi/spatial/blockAlgebra/BlockAlgebraConstraint.java.

Java's ``ReactangleToRCC``/``ReactangleToCardinalX``/``ReactangleToCardinalY``
composition tables (and the ``getRCCConstraint``/``getCardinalConstraint``
logic built on them) are declared identically -- copy-pasted verbatim -- in
both ``RectangleConstraint.java`` and this class. Rather than re-transcribing
the same 13x13 table a second time (a real transcription-error risk with no
behavioral difference), this port reuses the tables and helpers already
defined in ``rectangle_constraint.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from metacsp.framework.multi.multi_binary_constraint import MultiBinaryConstraint
from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import (
    RectangleConstraint,
    _make_cardinal_by_2dim,
    _ordinal,
)
from metacsp.spatial.cardinal.cardinal_constraint import CardinalConstraint
from metacsp.spatial.rcc.rcc_constraint import RCCConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.multi.spatial.block_algebra.rectangular_cuboid_region import (
        RectangularCuboidRegion,
    )

__all__ = ["BlockAlgebraConstraint"]

_Type = AllenIntervalConstraint.Type


def _java_array_str(types: list[AllenIntervalConstraint.Type]) -> str:
    """Mimics Java's ``Arrays.toString(Object[])``."""
    return "[" + ", ".join(t.name for t in types) + "]"


class BlockAlgebraConstraint(MultiBinaryConstraint):
    """A binary constraint over two :class:`RectangularCuboidRegion`
    variables: a triple of AllenIntervalConstraints, one per axis (X, Y, Z)
    -- the core relation of Block Algebra."""

    # Java declares its own copies of these three composition tables
    # (identical content to RectangleConstraint's -- see this module's
    # docstring); ported here as aliases onto RectangleConstraint's class
    # attributes rather than re-transcribed, to avoid a second copy of the
    # same error-prone 13x13 literal.
    RECTANGLE_TO_RCC: ClassVar[list[list[RCCConstraint.Type]]] = (
        RectangleConstraint.RECTANGLE_TO_RCC
    )
    RECTANGLE_TO_CARDINAL_X: ClassVar[list[CardinalConstraint.Type]] = (
        RectangleConstraint.RECTANGLE_TO_CARDINAL_X
    )
    RECTANGLE_TO_CARDINAL_Y: ClassVar[list[CardinalConstraint.Type]] = (
        RectangleConstraint.RECTANGLE_TO_CARDINAL_Y
    )

    def __init__(
        self,
        x_constraint: AllenIntervalConstraint,
        y_constraint: AllenIntervalConstraint,
        z_constraint: AllenIntervalConstraint,
    ) -> None:
        super().__init__()
        self.x_constraint = x_constraint
        self.y_constraint = y_constraint
        self.z_constraint = z_constraint
        # Ported verbatim, including the upstream bug: index 2 is assigned
        # yConstraint's types a second time instead of zConstraint's.
        self._type: list[list[AllenIntervalConstraint.Type]] = [
            x_constraint.types,
            y_constraint.types,
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
        return BlockAlgebraConstraint.RECTANGLE_TO_RCC[_ordinal(x)][_ordinal(y)]

    @property
    def internal_allen_interval_constraints(self) -> list[AllenIntervalConstraint]:
        return [self.x_constraint, self.y_constraint, self.z_constraint]

    @staticmethod
    def get_cardinal_constraint(c: BlockAlgebraConstraint) -> CardinalConstraint.Type | None:
        if c.type[0][0] == _Type.Equals and c.type[1][0] == _Type.Equals:
            return CardinalConstraint.Type.EQUAL
        return _make_cardinal_by_2dim(
            BlockAlgebraConstraint.RECTANGLE_TO_CARDINAL_X[_ordinal(c.type[0][0])],
            BlockAlgebraConstraint.RECTANGLE_TO_CARDINAL_Y[_ordinal(c.type[1][0])],
        )

    def create_internal_constraints_from_to(
        self, from_: Variable, to: Variable
    ) -> list[Constraint]:
        from_r = cast("RectangularCuboidRegion", from_)
        to_r = cast("RectangularCuboidRegion", to)
        self.x_constraint.from_ = from_r.internal_variables[0]
        self.x_constraint.to = to_r.internal_variables[0]
        self.y_constraint.from_ = from_r.internal_variables[1]
        self.y_constraint.to = to_r.internal_variables[1]
        self.z_constraint.from_ = from_r.internal_variables[2]
        self.z_constraint.to = to_r.internal_variables[2]
        solvers = cast(MultiVariable, from_r).internal_constraint_solvers
        # xConstraint should not be processed by the Y and Z solvers
        self.x_constraint.skip_solver(solvers[1], solvers[2])
        # yConstraint should not be processed by the X and Z solvers
        self.y_constraint.skip_solver(solvers[0], solvers[2])
        # zConstraint should not be processed by the X and Y solvers
        self.z_constraint.skip_solver(solvers[0], solvers[1])
        return [self.x_constraint, self.y_constraint, self.z_constraint]

    def is_equivalent(self, c: Constraint) -> bool:
        bc = cast(BlockAlgebraConstraint, c)
        internal = bc.internal_constraints
        assert internal is not None
        return (
            self.x_constraint.is_equivalent(internal[0])
            and self.y_constraint.is_equivalent(internal[1])
            and self.z_constraint.is_equivalent(internal[2])
        )

    def clone(self) -> BlockAlgebraConstraint:
        return BlockAlgebraConstraint(self.x_constraint, self.y_constraint, self.z_constraint)

    def __str__(self) -> str:
        ret = f"[{self.from_} ---"
        ret += (
            f"({_java_array_str(self.type[0])}, {_java_array_str(self.type[1])}, "
            f"{_java_array_str(self.type[2])})"
        )
        ret += f"--> ({self.to}]"
        return ret

    @property
    def edge_label(self) -> str:
        return (
            f"({_java_array_str(self.type[0])}, {_java_array_str(self.type[1])}, "
            f"{_java_array_str(self.type[2])})"
        )
