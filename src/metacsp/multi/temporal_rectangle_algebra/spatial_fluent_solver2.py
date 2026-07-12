"""Port of multi/temporalRectangleAlgebra/SpatialFluentSolver2.java."""

from __future__ import annotations

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.block_algebra.block_algebra_constraint import BlockAlgebraConstraint
from metacsp.multi.spatial.block_algebra.block_constraint_solver import BlockConstraintSolver
from metacsp.multi.spatial.block_algebra.unary_block_constraint import UnaryBlockConstraint
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent2 import SpatialFluent2

__all__ = ["SpatialFluentSolver2"]


class SpatialFluentSolver2(MultiConstraintSolver):
    """A MultiConstraintSolver composing a :class:`BlockConstraintSolver`
    (spatial placement) and an :class:`ActivityNetworkSolver` (temporal
    placement plus symbolic value), over :class:`SpatialFluent2`
    variables."""

    def __init__(self, origin: int, horizon: int, max_fluent: int | None = None) -> None:
        # Java's "protected int IDs = 0;" -- unused dead state (the
        # commented-out createVariablesSub that would have incremented it
        # is dead in the Java source too), kept for structural fidelity.
        self.ids = 0
        internal_solvers = self._create_constraint_solvers(
            origin, horizon, -1 if max_fluent is None else max_fluent
        )
        super().__init__(
            [
                BlockAlgebraConstraint,
                UnaryBlockConstraint,
                AllenIntervalConstraint,
                SymbolicValueConstraint,
            ],
            SpatialFluent2,
            internal_solvers,
            [1, 1],
        )

    @staticmethod
    def _create_constraint_solvers(
        origin: int, horizon: int, max_fluents: int
    ) -> list[ConstraintSolver]:
        if max_fluents != -1:
            return [
                BlockConstraintSolver(origin, horizon, max_fluents),
                ActivityNetworkSolver(origin, horizon, max_fluents),
            ]
        return [
            BlockConstraintSolver(origin, horizon),
            ActivityNetworkSolver(origin, horizon),
        ]

    def propagate(self) -> bool:
        return False
