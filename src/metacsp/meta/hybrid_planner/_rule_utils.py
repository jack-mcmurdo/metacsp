"""Shared helper collapsing a Bounds-copying idiom that the Java source
repeats near-identically half a dozen times across
``FluentBasedSimpleDomain.getSpatialConstraintNet``,
``MetaSpatialAdherenceConstraint.createTBOXspatialNetwork``,
``MetaSpatialAdherenceConstraint.isConflicting`` and
``MetaSpatialAdherenceConstraint.generateAllAlternativeSet``: given a
:class:`~metacsp.spatial.utility.spatial_rule.SpatialRule`, build a *fresh*
``UnaryRectangleConstraint``/``RectangleConstraint`` whose Bounds are copies
of the rule's own (so later constraint-solver propagation on the fresh
constraint can never mutate the rule template) -- falling back to
``.clone()`` for a param-less Allen type (empty bounds array), exactly as
the Java source does. Not a Java class of its own; collapsing the
duplication is a pure simplification (same computation, no behavior change).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.spatial.utility.spatial_rule import SpatialRule

__all__ = ["fresh_unary_size_constraint", "fresh_binary_constraint"]


def _fresh_bounds(bounds: list[Bounds]) -> tuple[Bounds, ...]:
    return tuple(Bounds(b.min, b.max) for b in bounds)


def fresh_unary_size_constraint(rule: SpatialRule) -> UnaryRectangleConstraint:
    return UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.Size, *_fresh_bounds(rule.unary_ra_constraint.bounds)
    )


def _fresh_axis_constraint(src: AllenIntervalConstraint) -> AllenIntervalConstraint:
    if not src.bounds:
        return src.clone()
    return AllenIntervalConstraint(src.types[0], *_fresh_bounds(src.bounds))


def fresh_binary_constraint(rule: SpatialRule) -> RectangleConstraint:
    x_src, y_src = rule.binary_ra_constraint.internal_allen_interval_constraints
    return RectangleConstraint(_fresh_axis_constraint(x_src), _fresh_axis_constraint(y_src))
