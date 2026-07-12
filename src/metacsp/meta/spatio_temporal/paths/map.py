"""Port of meta/spatioTemporal/paths/Map.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.meta.symbols_and_time.schedulable import Schedulable
from metacsp.multi.spatial.de9im.geometric_shape_domain import GeometricShapeDomain

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.multi.activity.activity import Activity
    from metacsp.multi.spatio_temporal.paths.trajectory_envelope import TrajectoryEnvelope

__all__ = ["Map"]


class Map(Schedulable):
    """A MetaConstraint stating that TrajectoryEnvelopes pertaining to
    different robots cannot overlap in time and in space."""

    def __init__(self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None) -> None:
        super().__init__(var_oh, val_oh)
        self.peak_collection_strategy = Schedulable.PEAKCOLLECTION.BINARY

    def is_conflicting(self, peak: list[Activity]) -> bool:
        if len(peak) < 2:
            return False
        te1 = cast("TrajectoryEnvelope", peak[0])
        te2 = cast("TrajectoryEnvelope", peak[1])
        if te1.robot_id == te2.robot_id:
            return False
        poly1 = te1.envelope_variable
        poly2 = te2.envelope_variable
        shape1 = cast(GeometricShapeDomain, poly1.domain).geometry
        shape2 = cast(GeometricShapeDomain, poly2.domain).geometry
        conflicting = shape1.intersects(shape2)
        if not conflicting:
            return False
        self.logger.debug("Resolving peak %s", peak)
        return True

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def __str__(self) -> str:
        return "---not implemented---"

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> Map | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def get_ground_solver(self) -> ConstraintSolver | None:
        return None
