"""Port of multi/temporalRectangleAlgebra/SpatialFluent.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.multi.multi_variable import MultiVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain
    from metacsp.framework.variable import Variable
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion
    from metacsp.spatial.reachability.configuration_variable import ConfigurationVariable

__all__ = ["SpatialFluent"]


class SpatialFluent(MultiVariable):
    """A MultiVariable combining a :class:`RectangularRegion` (spatial
    placement), a :class:`SymbolicVariableActivity` (temporal placement plus
    symbolic value), and a :class:`ConfigurationVariable` (reachability),
    managed by a :class:`SpatialFluentSolver`."""

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
        # "Activty" is a verbatim upstream typo in the printed string (kept
        # for observable-behavior fidelity, per C2/M13 notes -- it is text
        # content, not an identifier).
        return (
            "< Rectangle Variable: "
            + str(self.internal_variables[0])
            + ", Activty: "
            + str(self.internal_variables[1])
            + ",  Configurationvariable "
            + str(self.internal_variables[2])
            + ">"
        )

    @property
    def activity(self) -> SymbolicVariableActivity:
        return cast("SymbolicVariableActivity", self.internal_variables[1])

    @property
    def rectangular_region(self) -> RectangularRegion:
        return cast("RectangularRegion", self.internal_variables[0])

    @property
    def configuration_variable(self) -> ConfigurationVariable:
        return cast("ConfigurationVariable", self.internal_variables[2])
