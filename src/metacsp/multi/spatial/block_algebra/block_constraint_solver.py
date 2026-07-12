"""Port of multi/spatial/blockAlgebra/BlockConstraintSolver.java.

This class represents Block Algebra constraints. Each constraint represents
a three-dimensional Allen relation between spatial entities. In Block
Algebra, each spatial entity is restricted to be an axis-parallel bounding
box (cuboid).
"""

from __future__ import annotations

from enum import Enum
from typing import cast

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.allen_interval.allen_interval import AllenInterval
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.multi.spatial.block_algebra.block_algebra_constraint import BlockAlgebraConstraint
from metacsp.multi.spatial.block_algebra.rectangular_cuboid_region import RectangularCuboidRegion
from metacsp.multi.spatial.block_algebra.unary_block_constraint import UnaryBlockConstraint
from metacsp.multi.spatial.rectangle_algebra.bounding_box import BoundingBox
from metacsp.time.bounds import Bounds

__all__ = ["BlockConstraintSolver"]


class BlockConstraintSolver(MultiConstraintSolver):
    """A MultiConstraintSolver composing three AllenIntervalNetworkSolvers
    (one per axis) to reason about :class:`BlockAlgebraConstraint`\\ s /
    :class:`UnaryBlockConstraint`\\ s over :class:`RectangularCuboidRegion`
    variables."""

    class Dimension(Enum):
        X = 0
        Y = 1

    def __init__(self, origin: int, horizon: int, max_rectangles: int | None = None) -> None:
        internal_solvers = self._create_constraint_solvers(
            origin, horizon, -1 if max_rectangles is None else max_rectangles
        )
        super().__init__(
            [BlockAlgebraConstraint, UnaryBlockConstraint],
            RectangularCuboidRegion,
            internal_solvers,
            [1, 1, 1],
        )

    @staticmethod
    def _create_constraint_solvers(
        origin: int, horizon: int, max_rectangles: int
    ) -> list[ConstraintSolver]:
        if max_rectangles != -1:
            return [
                AllenIntervalNetworkSolver(origin, horizon, max_rectangles),  # X
                AllenIntervalNetworkSolver(origin, horizon, max_rectangles),  # Y
                AllenIntervalNetworkSolver(origin, horizon, max_rectangles),  # Z
            ]
        return [
            AllenIntervalNetworkSolver(origin, horizon),  # X
            AllenIntervalNetworkSolver(origin, horizon),  # Y
            AllenIntervalNetworkSolver(origin, horizon),  # Z
        ]

    def propagate(self) -> bool:
        # Do nothing, AllenIntervalNetworkSolver takes care of propagation...
        return True

    def extract_bounding_boxes_from_stps(
        self, rect: RectangularCuboidRegion | str
    ) -> BoundingBox | None:
        if isinstance(rect, RectangularCuboidRegion):
            ix = cast(AllenInterval, rect.internal_variables[0])
            iy = cast(AllenInterval, rect.internal_variables[1])
            iz = cast(AllenInterval, rect.internal_variables[2])
            return BoundingBox(
                Bounds(ix.est, ix.lst),
                Bounds(ix.eet, ix.let),
                Bounds(iy.est, iy.lst),
                Bounds(iy.eet, iy.let),
                Bounds(iz.est, iz.lst),
                Bounds(iz.eet, iz.let),
            )

        name = rect
        x_solver_vars = self.constraint_solvers[0].get_variables()
        y_solver_vars = self.constraint_solvers[1].get_variables()
        z_solver_vars = self.constraint_solvers[2].get_variables()
        for i, var in enumerate(self.constraint_network.get_variables()):
            region = cast(RectangularCuboidRegion, var)
            if region.name == name:
                ix = cast(AllenInterval, x_solver_vars[i])
                iy = cast(AllenInterval, y_solver_vars[i])
                iz = cast(AllenInterval, z_solver_vars[i])
                return BoundingBox(
                    Bounds(ix.est, ix.lst),
                    Bounds(ix.eet, ix.let),
                    Bounds(iy.est, iy.lst),
                    Bounds(iy.eet, iy.let),
                    Bounds(iz.est, iz.lst),
                    Bounds(iz.eet, iz.let),
                )
        return None

    def extract_all_bounding_boxes_from_stps(self) -> dict[str, BoundingBox]:
        ret: dict[str, BoundingBox] = {}
        x_solver_vars = self.constraint_solvers[0].get_variables()
        y_solver_vars = self.constraint_solvers[1].get_variables()
        z_solver_vars = self.constraint_solvers[2].get_variables()
        for i, var in enumerate(self.constraint_network.get_variables()):
            region = cast(RectangularCuboidRegion, var)
            ix = cast(AllenInterval, x_solver_vars[i])
            iy = cast(AllenInterval, y_solver_vars[i])
            iz = cast(AllenInterval, z_solver_vars[i])
            ret[region.name] = BoundingBox(
                Bounds(ix.est, ix.lst),
                Bounds(ix.eet, ix.let),
                Bounds(iy.est, iy.lst),
                Bounds(iy.eet, iy.let),
                Bounds(iz.est, iz.lst),
                Bounds(iz.eet, iz.let),
            )
        return ret

    def extract_bounding_boxes_from_stps_by_name(self, name: str) -> list[BoundingBox]:
        ret: list[BoundingBox] = []
        x_solver_vars = self.constraint_solvers[0].get_variables()
        y_solver_vars = self.constraint_solvers[1].get_variables()
        z_solver_vars = self.constraint_solvers[2].get_variables()
        for i, var in enumerate(self.constraint_network.get_variables()):
            region = cast(RectangularCuboidRegion, var)
            if region.name == name:
                ix = cast(AllenInterval, x_solver_vars[i])
                iy = cast(AllenInterval, y_solver_vars[i])
                iz = cast(AllenInterval, z_solver_vars[i])
                ret.append(
                    BoundingBox(
                        Bounds(ix.est, ix.lst),
                        Bounds(ix.eet, ix.let),
                        Bounds(iy.est, iy.lst),
                        Bounds(iy.eet, iy.let),
                        Bounds(iz.est, iz.lst),
                        Bounds(iz.eet, iz.let),
                    )
                )
        return ret
