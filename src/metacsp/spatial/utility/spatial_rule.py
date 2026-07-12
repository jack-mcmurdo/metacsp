"""Port of spatial/utility/SpatialRule.java.

The Java class has four constructors, overloaded by the (not yet ported,
see M13 ``multi/spatial/{rectangle_algebra,block_algebra}/``) type of the
third argument: ``UnaryRectangleConstraint``, ``UnaryBlockConstraint``,
``RectangleConstraint``, ``BlockAlgebraConstraint``. Python has no
constructor overloading, so this is ported as one constructor taking four
mutually-exclusive keyword arguments (named after the corresponding Java
getters) -- exactly one is supplied at any call site, preserving the Java
class's observable behavior (exactly one of the four fields ends up
populated; ``is_block_algebra`` set iff a block-algebra argument was given)
without requiring the M13 types to exist yet. Those types are typed ``Any``
here and will narrow once M13 lands.
"""

from __future__ import annotations

from typing import Any

__all__ = ["SpatialRule"]


class SpatialRule:
    """A named spatial rule pairing a SpatialAssertionalRelation with exactly one
    of a unary rectangle/block constraint or a binary rectangle/block-algebra constraint."""

    def __init__(
        self,
        from_: str,
        to: str,
        *,
        unary_ra_constraint: Any = None,
        unary_ba_constraint: Any = None,
        binary_ra_constraint: Any = None,
        binary_ba_constraint: Any = None,
    ) -> None:
        self._from = from_
        self._to = to
        self._unary_ra_constraint = unary_ra_constraint
        self._unary_ba_constraint = unary_ba_constraint
        self._binary_ra_constraint = binary_ra_constraint
        self._binary_ba_constraint = binary_ba_constraint
        self._is_block_algebra = unary_ba_constraint is not None or binary_ba_constraint is not None

    @property
    def to(self) -> str:
        return self._to

    @property
    def from_(self) -> str:
        return self._from

    @property
    def unary_ra_constraint(self) -> Any:
        return self._unary_ra_constraint

    @property
    def unary_ba_constraint(self) -> Any:
        return self._unary_ba_constraint

    @property
    def binary_ra_constraint(self) -> Any:
        return self._binary_ra_constraint

    @property
    def binary_ba_constraint(self) -> Any:
        return self._binary_ba_constraint

    def __str__(self) -> str:
        if self._is_block_algebra:
            if self._binary_ba_constraint is not None:
                return f"({self.from_}) --{self._binary_ba_constraint}--> ({self.to})"
            if self._unary_ba_constraint is not None:
                return f"({self.from_}) --{self._unary_ba_constraint}--> ({self.to})"
        else:
            if self._binary_ra_constraint is not None:
                return f"({self.from_}) --{self._binary_ra_constraint}--> ({self.to})"
            if self._unary_ra_constraint is not None:
                return f"({self.from_}) --{self._unary_ra_constraint}--> ({self.to})"
        # Unreachable given the constructor invariants above (Java falls
        # through to `return null` here).
        return "None"
