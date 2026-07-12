"""Port of multi/temporalRectangleAlgebra/SpatialFluent2.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.multi.multi_variable import MultiVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain
    from metacsp.framework.variable import Variable
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.multi.spatial.block_algebra.rectangular_cuboid_region import (
        RectangularCuboidRegion,
    )

__all__ = ["SpatialFluent2"]


class SpatialFluent2(MultiVariable):
    """A MultiVariable combining a :class:`RectangularCuboidRegion` (spatial
    placement) and a :class:`SymbolicVariableActivity` (temporal placement
    plus symbolic value), managed by a :class:`SpatialFluentSolver2`."""

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

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    def __str__(self) -> str:
        return (
            "< RectangulatCuboidRegion: "
            + str(self.internal_variables[0])
            + ", Activty: "
            + str(self.internal_variables[1])
            + ">"
        )

    @property
    def activity(self) -> SymbolicVariableActivity:
        return cast("SymbolicVariableActivity", self.internal_variables[1])

    @property
    def rectangular_cuboid_region(self) -> RectangularCuboidRegion:
        return cast("RectangularCuboidRegion", self.internal_variables[0])
