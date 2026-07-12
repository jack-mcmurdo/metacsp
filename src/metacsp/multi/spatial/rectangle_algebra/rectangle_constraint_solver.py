"""Port of multi/spatial/rectangleAlgebra/RectangleConstraintSolver.java.

This class represents Rectangle constraints. Each constraint represents a
two-dimensional Allen relation between spatial entities. In Rectangle
Algebra, each spatial entity is restricted to be an axis-parallel rectangle.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.allen_interval.allen_interval import AllenInterval
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.multi.spatial.rectangle_algebra.bounding_box import AwtRectangle, BoundingBox
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangular_region import RectangularRegion
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.time.bounds import Bounds

__all__ = ["RectangleConstraintSolver"]


class RectangleConstraintSolver(MultiConstraintSolver):
    """A MultiConstraintSolver composing two AllenIntervalNetworkSolvers (one
    per axis) to reason about :class:`RectangleConstraint`\\ s /
    :class:`UnaryRectangleConstraint`\\ s over :class:`RectangularRegion`
    variables."""

    class Dimension(Enum):
        X = 0
        Y = 1

    def __init__(self, origin: int, horizon: int, max_rectangles: int | None = None) -> None:
        if max_rectangles is None:
            # Java's 2-arg constructor.
            constraint_types: list[type] = [RectangleConstraint, UnaryRectangleConstraint]
            internal_solvers = self._create_constraint_solvers(origin, horizon, -1)
        else:
            # Java's 3-arg constructor -- note it registers only
            # RectangleConstraint, dropping UnaryRectangleConstraint; ported
            # verbatim (see M13 porting notes: the Java source is the oracle
            # for observable behavior).
            constraint_types = [RectangleConstraint]
            internal_solvers = self._create_constraint_solvers(origin, horizon, max_rectangles)
        super().__init__(constraint_types, RectangularRegion, internal_solvers, [1, 1])
        self.horizon = horizon
        self.filtering_boxes: list[BoundingBox] = []
        # Java's ``this.setOptions(org.metacsp.framework.ConstraintSolver
        # .OPTIONS.AUTO_PROPAGATE)`` call resolves, via Java's static
        # overload resolution, to the *base* ConstraintSolver.setOptions
        # (not MultiConstraintSolver's shadowing setOptions(OPTIONS...),
        # which only accepts its own nested OPTIONS type) because the
        # argument's static type is ConstraintSolver.OPTIONS. Python has no
        # overload resolution -- calling ``self.set_options(...)`` here
        # would silently hit MultiConstraintSolver.set_options and no-op.
        # Call the base implementation directly to replicate Java's actual
        # (if accidental) behavior.
        ConstraintSolver.set_options(self, ConstraintSolver.Options.AUTO_PROPAGATE)

    @staticmethod
    def _create_constraint_solvers(
        origin: int, horizon: int, max_rectangles: int
    ) -> list[ConstraintSolver]:
        if max_rectangles != -1:
            return [
                AllenIntervalNetworkSolver(origin, horizon, max_rectangles),  # X
                AllenIntervalNetworkSolver(origin, horizon, max_rectangles),  # Y
            ]
        return [
            AllenIntervalNetworkSolver(origin, horizon),  # X
            AllenIntervalNetworkSolver(origin, horizon),  # Y
        ]

    def propagate(self) -> bool:
        # Do nothing, AllenIntervalNetworkSolver takes care of propagation...
        if self.filtering_boxes:
            for var in self.get_variables():
                region = cast(RectangularRegion, var)
                region_rect = region.get_bounding_box().get_almost_centre_rectangle()
                for box in self.filtering_boxes:
                    if region_rect.intersects(box.get_almost_centre_rectangle()):
                        return False
        return True

    def draw_almost_centre_rectangle(self, horizon: int, *rect: RectangularRegion) -> str:
        """Output a Gnuplot-readable script that draws, for each given
        RectangularRegion, a rectangle close to the "center" of the
        RectangularRegion's domain."""
        ret = f"set xrange [0:{horizon}]\n"
        ret += f"set yrange [0:{horizon}]\n"
        j = 1
        for i, region in enumerate(rect):
            box = self.extract_bounding_boxes_from_stps(region).get_almost_centre_rectangle()
            ret += (
                f"set obj {j} rect from {box.min_x},{box.min_y} to {box.max_x},{box.max_y} "
                f"front fs transparent solid 0.0 border {i + 1} lw 0.5\n"
            )
            j += 1
            ret += (
                f'set label "{region}-c" at {box.center_x},{box.center_y} '
                f'textcolor lt {i + 1} font "9"\n'
            )
            j += 1
        ret += "plot NaN\n"
        ret += "pause -1"
        return ret

    def draw_almost_centre_rectangle_by_name(
        self, horizon: int, rect: dict[str, AwtRectangle]
    ) -> str:
        """The Java overload ``drawAlmostCentreRectangle(long, Map<String,
        Rectangle>)`` -- renamed with a ``_by_name`` suffix since Python does
        not resolve overloads by parameter type (matching the existing
        ``extract_bounding_boxes_from_stps_by_name`` naming convention below
        for the same situation)."""
        ret = f"set xrange [0:{horizon}]\n"
        ret += f"set yrange [0:{horizon}]\n"
        j = 1
        for i, (name, box) in enumerate(rect.items()):
            ret += (
                f"set obj {j} rect from {box.min_x},{box.min_y} to {box.max_x},{box.max_y} "
                f"front fs transparent solid 0.0 border {i + 1} lw 2\n"
            )
            j += 1
            ret += f'set label "{name}" at {box.center_x},{box.center_y} textcolor lt {i + 1} font "9"\n'
            j += 1
        ret += "plot NaN\n"
        ret += "pause -1"
        return ret

    def extract_bounding_boxes_from_stps(self, rect: RectangularRegion | str) -> BoundingBox | None:
        if isinstance(rect, RectangularRegion):
            interval_x = cast(AllenInterval, rect.internal_variables[0])
            interval_y = cast(AllenInterval, rect.internal_variables[1])
            x_lb = Bounds(interval_x.est, interval_x.lst)
            x_ub = Bounds(interval_x.eet, interval_x.let)
            y_lb = Bounds(interval_y.est, interval_y.lst)
            y_ub = Bounds(interval_y.eet, interval_y.let)
            return BoundingBox(x_lb, x_ub, y_lb, y_ub)

        name = rect
        x_solver_vars = self.constraint_solvers[0].get_variables()
        y_solver_vars = self.constraint_solvers[1].get_variables()
        for i, var in enumerate(self.constraint_network.get_variables()):
            region = cast(RectangularRegion, var)
            if region.name == name:
                ix = cast(AllenInterval, x_solver_vars[i])
                iy = cast(AllenInterval, y_solver_vars[i])
                x_lb = Bounds(ix.est, ix.lst)
                x_ub = Bounds(ix.eet, ix.let)
                y_lb = Bounds(iy.est, iy.lst)
                y_ub = Bounds(iy.eet, iy.let)
                return BoundingBox(x_lb, x_ub, y_lb, y_ub)
        return None

    def extract_all_bounding_boxes_from_stps(self) -> dict[str, BoundingBox]:
        ret: dict[str, BoundingBox] = {}
        x_solver_vars = self.constraint_solvers[0].get_variables()
        y_solver_vars = self.constraint_solvers[1].get_variables()
        for i, var in enumerate(self.constraint_network.get_variables()):
            region = cast(RectangularRegion, var)
            ix = cast(AllenInterval, x_solver_vars[i])
            iy = cast(AllenInterval, y_solver_vars[i])
            x_lb = Bounds(ix.est, ix.lst)
            x_ub = Bounds(ix.eet, ix.let)
            y_lb = Bounds(iy.est, iy.lst)
            y_ub = Bounds(iy.eet, iy.let)
            ret[region.name] = BoundingBox(x_lb, x_ub, y_lb, y_ub)
        return ret

    def extract_bounding_boxes_from_stps_by_name(self, name: str) -> list[BoundingBox]:
        ret: list[BoundingBox] = []
        x_solver_vars = self.constraint_solvers[0].get_variables()
        y_solver_vars = self.constraint_solvers[1].get_variables()
        for i, var in enumerate(self.constraint_network.get_variables()):
            region = cast(RectangularRegion, var)
            if region.name == name:
                ix = cast(AllenInterval, x_solver_vars[i])
                iy = cast(AllenInterval, y_solver_vars[i])
                x_lb = Bounds(ix.est, ix.lst)
                x_ub = Bounds(ix.eet, ix.let)
                y_lb = Bounds(iy.est, iy.lst)
                y_ub = Bounds(iy.eet, iy.let)
                ret.append(BoundingBox(x_lb, x_ub, y_lb, y_ub))
        return ret

    def set_filtering_area(self, boxes: list[BoundingBox]) -> None:
        self.filtering_boxes = list(boxes)
