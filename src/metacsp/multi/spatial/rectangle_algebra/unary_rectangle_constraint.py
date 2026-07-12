"""Port of multi/spatial/rectangleAlgebra/UnaryRectangleConstraint.java."""

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
    from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion

__all__ = ["UnaryRectangleConstraint"]


class UnaryRectangleConstraint(MultiBinaryConstraint):
    """A unary constraint (both ends of its scope are the same
    RectangularRegion) fixing a region's size (``Size``, two Bounds: X and Y
    duration) or absolute placement (``At``, four Bounds: X-EST/X-EET,
    Y-EST/Y-EET)."""

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
        from_r = cast("RectangularRegion", from_)
        if self.type is UnaryRectangleConstraint.Type.Size:
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
            # xConstraint should not be processed by the Y solver
            duration_x.skip_solver(cast(MultiVariable, from_r).internal_constraint_solvers[1])
            # yConstraint should not be processed by the X solver
            duration_y.skip_solver(cast(MultiVariable, from_r).internal_constraint_solvers[0])
            return [duration_x, duration_y]
        if self.type is UnaryRectangleConstraint.Type.At:
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
            # xConstraint should not be processed by the Y solver
            at_x.skip_solver(cast(MultiVariable, from_r).internal_constraint_solvers[1])
            # yConstraint should not be processed by the X solver
            at_y.skip_solver(cast(MultiVariable, from_r).internal_constraint_solvers[0])
            return [at_x, at_y]
        return None

    def clone(self) -> UnaryRectangleConstraint:
        return UnaryRectangleConstraint(self.type, *self.bounds)

    @property
    def edge_label(self) -> str:
        return f"{self.type}{list(self.bounds)}"

    def is_equivalent(self, c: Constraint) -> bool:
        if not isinstance(c, UnaryRectangleConstraint) or c.type != self.type:
            return False
        # Ported verbatim, oddities and all: the inner loop's early-return
        # only fires on its last iteration, so this checks that every bound
        # of ``c`` equals *some* bound of ``self`` -- not a true set/order
        # equality check.
        for i in range(len(c.bounds)):
            for j in range(len(self.bounds)):
                if c.bounds[i] == self.bounds[j]:
                    continue
                elif i == len(c.bounds) - 1:
                    return False
        return True
