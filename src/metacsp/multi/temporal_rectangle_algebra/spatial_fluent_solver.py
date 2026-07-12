"""Port of multi/temporalRectangleAlgebra/SpatialFluentSolver.java."""

from __future__ import annotations

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint_solver import (
    RectangleConstraintSolver,
)
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent import SpatialFluent
from metacsp.spatial.reachability.reachability_constraint import ReachabilityConstraint
from metacsp.spatial.reachability.reachability_constraint_solver import (
    ReachabilityConstraintSolver,
)

__all__ = ["SpatialFluentSolver"]


class SpatialFluentSolver(MultiConstraintSolver):
    """A MultiConstraintSolver composing a :class:`RectangleConstraintSolver`
    (spatial placement), an :class:`ActivityNetworkSolver` (temporal
    placement plus symbolic value), and a
    :class:`ReachabilityConstraintSolver`, over :class:`SpatialFluent`
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
                RectangleConstraint,
                UnaryRectangleConstraint,
                AllenIntervalConstraint,
                SymbolicValueConstraint,
                ReachabilityConstraint,
            ],
            SpatialFluent,
            internal_solvers,
            [1, 1, 1],
        )

    @staticmethod
    def _create_constraint_solvers(
        origin: int, horizon: int, max_fluents: int
    ) -> list[ConstraintSolver]:
        if max_fluents != -1:
            return [
                RectangleConstraintSolver(origin, horizon, max_fluents),
                ActivityNetworkSolver(origin, horizon, max_fluents),
                ReachabilityConstraintSolver(),
            ]
        return [
            RectangleConstraintSolver(origin, horizon),
            ActivityNetworkSolver(origin, horizon),
            ReachabilityConstraintSolver(),
        ]

    def propagate(self) -> bool:
        return False
