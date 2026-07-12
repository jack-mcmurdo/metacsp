"""Port of multi/spatial/blockAlgebra/UnaryBlockConstraint.java."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, cast

from metacsp.framework.multi.multi_binary_constraint import MultiBinaryConstraint
from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.multi.spatial.block_algebra.rectangular_cuboid_region import (
        RectangularCuboidRegion,
    )

__all__ = ["UnaryBlockConstraint"]


class UnaryBlockConstraint(MultiBinaryConstraint):
    """A unary constraint (both ends of its scope are the same
    RectangularCuboidRegion) fixing a region's size (``Size``, three Bounds:
    X/Y/Z duration) or absolute placement (``At``, six Bounds: X-EST/X-EET,
    Y-EST/Y-EET, Z-EST/Z-EET)."""

    class Type(Enum):
        Size = 0
        At = 1

    def __init__(self, t: Type, *bounds: Bounds) -> None:
        super().__init__()
        self.type = t
        self.bounds: tuple[Bounds, ...] = bounds

    def create_internal_constraints_from_to(
        self, from_: Variable, to: Variable
    ) -> list[Constraint] | None:
        from_r = cast("RectangularCuboidRegion", from_)
        solvers = cast(MultiVariable, from_r).internal_constraint_solvers
        if self.type is UnaryBlockConstraint.Type.Size:
            duration_x = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Duration, self.bounds[0]
            )
            duration_x.from_ = from_r.internal_variables[0]
            duration_x.to = from_r.internal_variables[0]
            duration_y = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Duration, self.bounds[1]
            )
            duration_y.from_ = from_r.internal_variables[1]
            duration_y.to = from_r.internal_variables[1]
            duration_z = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Duration, self.bounds[2]
            )
            duration_z.from_ = from_r.internal_variables[2]
            duration_z.to = from_r.internal_variables[2]
            # xConstraint should not be processed by the Y and Z solvers
            duration_x.skip_solver(solvers[1], solvers[2])
            # yConstraint should not be processed by the X and Z solvers
            duration_y.skip_solver(solvers[0], solvers[2])
            # zConstraint should not be processed by the X and Y solvers
            duration_z.skip_solver(solvers[0], solvers[1])
            return [duration_x, duration_y, duration_z]
        if self.type is UnaryBlockConstraint.Type.At:
            at_x = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.At, self.bounds[0], self.bounds[1]
            )
            at_x.from_ = from_r.internal_variables[0]
            at_x.to = from_r.internal_variables[0]
            at_y = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.At, self.bounds[2], self.bounds[3]
            )
            at_y.from_ = from_r.internal_variables[1]
            at_y.to = from_r.internal_variables[1]
            at_z = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.At, self.bounds[4], self.bounds[5]
            )
            at_z.from_ = from_r.internal_variables[2]
            at_z.to = from_r.internal_variables[2]
            # xConstraint should not be processed by the Y and Z solvers
            at_x.skip_solver(solvers[1], solvers[2])
            # yConstraint should not be processed by the X and Z solvers
            at_y.skip_solver(solvers[0], solvers[2])
            # zConstraint should not be processed by the X and Y solvers
            at_z.skip_solver(solvers[0], solvers[1])
            return [at_x, at_y, at_z]
        return None

    def clone(self) -> UnaryBlockConstraint:
        return UnaryBlockConstraint(self.type, *self.bounds)

    @property
    def edge_label(self) -> str:
        return f"{self.type}{list(self.bounds)}"

    def is_equivalent(self, c: Constraint) -> bool:
        if not isinstance(c, UnaryBlockConstraint) or c.type != self.type:
            return False
        # Ported verbatim (see UnaryRectangleConstraint.is_equivalent for the
        # same not-quite-set-equality logic).
        for i in range(len(c.bounds)):
            for j in range(len(self.bounds)):
                if c.bounds[i] == self.bounds[j]:
                    continue
                elif i == len(c.bounds) - 1:
                    return False
        return True
