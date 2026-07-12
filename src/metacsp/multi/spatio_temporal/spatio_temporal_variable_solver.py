"""Port of multi/spatioTemporal/SpatioTemporalVariableSolver.java.

The protected ``SpatioTemporalVariableSolver(Class<?>[], Class<?>,
ConstraintSolver[], int[])`` constructor (present in Java for subclassing,
but never actually subclassed anywhere in the codebase) passed reflection
``Class<?>`` objects through to ``MultiConstraintSolver``; per C5 it is
dropped here (mirrors ``DE9IMRelationSolver``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.multi.spatial.de9im.de9im_relation import DE9IMRelation
from metacsp.multi.spatial.de9im.de9im_relation_solver import DE9IMRelationSolver
from metacsp.multi.spatio_temporal.spatio_temporal_variable import SpatioTemporalVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["SpatioTemporalVariableSolver"]


class SpatioTemporalVariableSolver(MultiConstraintSolver):
    """A MultiConstraintSolver for SpatioTemporalVariables. Constraints of
    type AllenIntervalConstraint and DE9IMRelation can be added to
    SpatioTemporalVariables."""

    def __init__(self, origin: int, horizon: int) -> None:
        super().__init__(
            [AllenIntervalConstraint, DE9IMRelation],
            SpatioTemporalVariable,
            self._create_internal_constraint_solvers(origin, horizon),
            [1, 1],
        )

    @staticmethod
    def _create_internal_constraint_solvers(origin: int, horizon: int) -> list[ConstraintSolver]:
        return [AllenIntervalNetworkSolver(origin, horizon), DE9IMRelationSolver()]

    def propagate(self) -> bool:
        return True

    def get_temporal_solver(self) -> AllenIntervalNetworkSolver:
        """The AllenIntervalNetworkSolver which propagates temporal
        constraints (of type AllenIntervalConstraint) among the temporal
        parts (AllenIntervals) of SpatioTemporalVariables."""
        return cast(AllenIntervalNetworkSolver, self.constraint_solvers[0])

    def get_spatial_solver(self) -> DE9IMRelationSolver:
        """The DE9IMRelationSolver which propagates spatial constraints (of
        type DE9IMRelation) among the spatial parts (GeometricShapeVariables)
        of SpatioTemporalVariables."""
        return cast(DE9IMRelationSolver, self.constraint_solvers[1])
