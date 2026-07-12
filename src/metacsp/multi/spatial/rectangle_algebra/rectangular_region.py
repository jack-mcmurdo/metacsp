"""Port of multi/spatial/rectangleAlgebra/RectangularRegion.java.

The Java class also carries ``getOntologicalProp``/``setOntologicalProp``,
backed by ``multi.spatial.rectangleAlgebraNew.toRemove.OntologicalSpatialProperty``.
Per PLAN.md's skip list, ``rectangleAlgebraNew`` (dead code marked for
upstream removal) is not ported, so those two methods -- unused by anything
in scope through M13 -- are omitted here as well.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.multi.spatial.rectangle_algebra.bounding_box import BoundingBox
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain
    from metacsp.framework.variable import Variable
    from metacsp.multi.allen_interval.allen_interval import AllenInterval
    from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint_solver import (
        RectangleConstraintSolver,
    )

__all__ = ["RectangularRegion"]


class RectangularRegion(MultiVariable):
    """A MultiVariable representing an axis-parallel rectangle: a pair of
    AllenIntervals (one per axis), managed by a
    :class:`RectangleConstraintSolver`."""

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id, internal_solvers, internal_vars)
        self.name = ""

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        return None

    @property
    def domain(self) -> Domain:
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        pass

    def __str__(self) -> str:
        # Java's ``name != null`` guard is unconditionally true here: ``name``
        # is initialized to "" (never None) in both languages.
        return f"{{{type(self).__name__} {self.name} {self.domain}}}"

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    def is_unbounded(self) -> bool:
        interval_x = cast("AllenInterval", self.internal_variables[0])
        interval_y = cast("AllenInterval", self.internal_variables[1])

        x_lb = Bounds(interval_x.est, interval_x.lst)
        x_ub = Bounds(interval_x.eet, interval_x.let)
        y_lb = Bounds(interval_y.est, interval_y.lst)
        y_ub = Bounds(interval_y.eet, interval_y.let)
        horizon = cast("RectangleConstraintSolver", self.constraint_solver).horizon

        # Ported verbatim, including the upstream bug: the last conjunct
        # re-checks ``y_lb.min == 0`` instead of ``y_ub.min == 0``.
        if (
            (x_lb.min == 0 and x_lb.max == horizon)
            and (x_ub.min == 0 and x_ub.max == horizon)
            and (y_lb.min == 0 and y_lb.max == horizon)
            and (y_lb.min == 0 and y_ub.max == horizon)
        ):
            return True
        return False

    def get_bounding_box(self) -> BoundingBox:
        interval_x = cast("AllenInterval", self.internal_variables[0])
        interval_y = cast("AllenInterval", self.internal_variables[1])

        x_lb = Bounds(interval_x.est, interval_x.lst)
        x_ub = Bounds(interval_x.eet, interval_x.let)
        y_lb = Bounds(interval_y.est, interval_y.lst)
        y_ub = Bounds(interval_y.eet, interval_y.let)

        return BoundingBox(x_lb, x_ub, y_lb, y_ub)
