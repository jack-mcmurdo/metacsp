"""Port of multi/spatioTemporal/SpatioTemporalVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.multi.spatial.de9im.geometric_shape_domain import GeometricShapeDomain
from metacsp.multi.spatial.de9im.geometric_shape_variable import GeometricShapeVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable
    from metacsp.multi.allen_interval.allen_interval import AllenInterval

__all__ = ["SpatioTemporalVariable"]


class SpatioTemporalVariable(MultiVariable):
    """A MultiVariable composed of an AllenInterval (temporal part) and a
    GeometricShapeVariable (spatial part). Constraints of type
    AllenIntervalConstraint and DE9IMRelation can be added to
    SpatioTemporalVariables."""

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id, internal_solvers, internal_vars)

    def __lt__(self, other: Variable) -> bool:
        # Java's compareTo is an unfinished stub that always returns 0.
        return False

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        return None

    @property
    def domain(self) -> Any:
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        if isinstance(d, GeometricShapeDomain):
            self.internal_variables[1].domain = d

    def __str__(self) -> str:
        return str(self.id)

    @property
    def temporal_variable(self) -> AllenInterval:
        """The temporal part of this SpatioTemporalVariable."""
        return cast("AllenInterval", self.internal_variables[0])

    @property
    def spatial_variable(self) -> GeometricShapeVariable:
        """The spatial part of this SpatioTemporalVariable."""
        return cast(GeometricShapeVariable, self.internal_variables[1])
