"""Port of multi/spatial/blockAlgebra/RectangularCuboidRegion.java.

The Java class also carries ``getOntologicalProp``/``setOntologicalProp``,
backed by ``multi.spatial.rectangleAlgebraNew.toRemove.OntologicalSpatialProperty``.
Per PLAN.md's skip list, ``rectangleAlgebraNew`` (dead code marked for
upstream removal) is not ported, so those two methods -- unused by anything
in scope through M13 -- are omitted here as well (mirrors
``RectangularRegion``, see that module's docstring).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from metacsp.framework.multi.multi_variable import MultiVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain
    from metacsp.framework.variable import Variable

__all__ = ["RectangularCuboidRegion"]


class RectangularCuboidRegion(MultiVariable):
    """A MultiVariable representing an axis-parallel cuboid: a triple of
    AllenIntervals (one per axis), managed by a
    :class:`~metacsp.multi.spatial.block_algebra.block_constraint_solver.BlockConstraintSolver`."""

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
        return f"{{{type(self).__name__} {self.name} {self.domain}}}"

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id
