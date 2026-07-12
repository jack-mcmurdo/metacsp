"""Port of spatial/utility/SpatialAssertionalRelation.java.

``OntologicalSpatialProperty`` (``multi/spatial/rectangleAlgebraNew/toRemove/``)
is on the skip list (dead code marked for removal upstream) and is not
ported; ``ontological_prop`` is typed ``Any`` here and simply carries
whatever value is set on it. ``UnaryRectangleConstraint``/
``UnaryBlockConstraint`` are M13 types (``multi/spatial/{rectangle_algebra,
block_algebra}/``), not yet ported -- also typed ``Any`` for now and will
narrow once M13 lands.
"""

from __future__ import annotations

from typing import Any

from metacsp.spatial.utility.assertional_relation import AssertionalRelation

__all__ = ["SpatialAssertionalRelation"]


class SpatialAssertionalRelation(AssertionalRelation):
    """An AssertionalRelation additionally carrying an ontological spatial
    property and/or a unary rectangle/block-algebra constraint."""

    def __init__(self, from_: str, to: str) -> None:
        super().__init__(from_, to)
        self._ontological_prop: Any = None
        self._unary_ra_constraint: Any = None
        self._unary_ba_constraint: Any = None

    @property
    def unary_at_rectangle_constraint(self) -> Any:
        return self._unary_ra_constraint

    @unary_at_rectangle_constraint.setter
    def unary_at_rectangle_constraint(self, value: Any) -> None:
        self._unary_ra_constraint = value

    @property
    def unary_at_block_constraint(self) -> Any:
        return self._unary_ba_constraint

    @unary_at_block_constraint.setter
    def unary_at_block_constraint(self, value: Any) -> None:
        self._unary_ba_constraint = value

    @property
    def ontological_prop(self) -> Any:
        return self._ontological_prop

    @ontological_prop.setter
    def ontological_prop(self, value: Any) -> None:
        self._ontological_prop = value
