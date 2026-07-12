"""Port of spatial/geometry/GeometricConstraintSolver.java.

``getInsideVertices`` used ``java.awt.Polygon.contains`` (scaling coordinates
to ints, since ``java.awt.Polygon`` only stores integer vertices) as a
point-in-polygon test. Per D4 this package stays free of Shapely, so that
test is replaced here with a standard float-based even-odd ray-casting
test (``_contains``), which is equivalent for the simple polygons this
solver deals with and needs no int-scaling workaround.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.spatial.geometry.geometric_constraint import GeometricConstraint
from metacsp.spatial.geometry.manifold import Manifold
from metacsp.spatial.geometry.polygon import MAX_X, MAX_Y, MIN_X, MIN_Y, Polygon
from metacsp.spatial.geometry.rcc2_constraint_solver import RCC2ConstraintSolver
from metacsp.spatial.geometry.sutherland_hodgman import SutherlandHodgman
from metacsp.spatial.geometry.vec2 import Vec2

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["GeometricConstraintSolver"]


def _contains(vertices: list[Vec2], x: float, y: float) -> bool:
    """Even-odd ray-casting point-in-polygon test."""
    inside = False
    n = len(vertices)
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i].x, vertices[i].y
        xj, yj = vertices[j].x, vertices[j].y
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


class GeometricConstraintSolver(RCC2ConstraintSolver):
    """An RCC2ConstraintSolver extended with GeometricConstraint (DC/INSIDE)
    checks based on Polygon collision detection."""

    # Min and max dimensions of the Euclidean space.
    MAX_X = MAX_X
    MAX_Y = MAX_Y
    MIN_X = MIN_X
    MIN_Y = MIN_Y

    def __init__(self) -> None:
        super().__init__()
        self._constraint_track: dict[GeometricConstraint, dict[Polygon, list[Vec2]]] = {}
        self._obstacles: list[Variable] | None = None
        self.set_options(RCC2ConstraintSolver.Options.AUTO_PROPAGATE)

    def propagate(self) -> bool:
        if not super().propagate():
            return False
        cons = self.get_constraints()
        for con in cons:
            gc = cast(GeometricConstraint, con)
            if not super().propagate():
                return False
            if gc.type is GeometricConstraint.Type.DC:
                manifold = Manifold(gc.from_, gc.to)
                if manifold.is_collided():
                    if not gc.from_.is_movable:
                        return False
                    self.logger.debug(
                        "PROPAGATED DC between Polygon %s Polygon %s", gc.from_.id, gc.to.id
                    )
                    self._apply_polygon_separation(gc.from_, gc.to)
            elif gc.type is GeometricConstraint.Type.INSIDE:
                self._apply_inside(gc.from_, gc.to)
                self.logger.debug(
                    "PROPAGATED INSIDE between Polygon %s Polygon %s", gc.from_.id, gc.to.id
                )
        return True

    @staticmethod
    def get_relation(p1: Polygon, p2: Polygon) -> GeometricConstraint.Type:
        if GeometricConstraintSolver._check_inside(p1, p2):
            return GeometricConstraint.Type.INSIDE
        return GeometricConstraint.Type.DC

    @staticmethod
    def _check_inside(p1: Polygon, p2: Polygon) -> bool:
        epsilon = 0.003
        # arg 2 will be clipped, arg 1 is clipper.
        slh = SutherlandHodgman(p2, p1)
        clipped = slh.get_clipped_result()
        for v in p1.get_full_space_representation():
            found = False
            for cv in clipped:
                if abs(v.x - cv.x) < epsilon and abs(v.y - cv.y) < epsilon:
                    found = True
            if not found:
                return False
        return True

    def _get_inside_vertices(self, p1: Polygon, p2: Polygon) -> list[Vec2]:
        ret: list[Vec2] = []
        p2_full = p2.get_full_space_representation()
        for v in p1.get_full_space_representation():
            if _contains(p2_full, v.x, v.y):
                ret.append(v)
        return ret

    def _apply_inside(self, p1: Polygon, p2: Polygon) -> bool:
        difx = p2.position.x - p1.position.x
        dify = p2.position.y - p1.position.y
        p1_full = p1.get_full_space_representation()
        p1_copy = [Vec2(v.x, v.y) for v in p1_full]
        p1_domain = [Vec2(v.x + difx, v.y + dify) for v in p1_full]
        p1.set_domain(*p1_domain)
        if self._check_inside(p1, p2):
            p1.set_orientation(p2.get_orientation())
            return True
        p1.set_domain(*p1_copy)
        return False

    @staticmethod
    def get_intersection_polygon(p1: Polygon, p2: Polygon) -> list[Vec2]:
        slh = SutherlandHodgman(p1, p2)
        return slh.get_clipped_result()

    def apply_dc_cliping(self, p1: Polygon, p2: Polygon) -> bool:
        slh = SutherlandHodgman(p1, p2)
        to_be_added = slh.get_contact_points()
        to_be_removed = self._get_inside_vertices(p1, p2)

        # Remove the vertices inside the other polygon.
        epsilon = 0.003
        new_domain: list[Vec2] = []
        for v in p1.get_full_space_representation():
            found = False
            for rv in to_be_removed:
                if abs(v.x - rv.x) < epsilon and abs(v.y - rv.y) < epsilon:
                    found = True
            if not found:
                new_domain.append(v)

        # Add the to-be contact vertices.
        for av in to_be_added:
            new_domain.append(av)

        p1.set_domain(*new_domain)

        manifold = Manifold(p1, p2)
        return not manifold.is_collided()

    @staticmethod
    def get_area(vertices: list[Vec2]) -> float:
        ret = 0.0
        for i in range(len(vertices) - 1):
            ret += (vertices[i].x * vertices[i + 1].y) - (vertices[i].y * vertices[i + 1].x)
        ret = ret / 2.0
        return abs(ret)

    def _apply_polygon_separation(self, p1: Polygon, p2: Polygon) -> bool:
        manifold = Manifold(p1, p2)
        if manifold.solve():
            manifold.positional_correction()
        return True

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        cons = c
        for i in range(len(cons)):
            gc = cast(GeometricConstraint, cons[i])
            # Handling movable property.
            if not gc.from_.is_movable:
                return self._verify_situation(gc)
            # If there is already any constraint between the scopes of the
            # added constraint, reject the constraint.
            existing = self.get_constraints(gc.from_, gc.to)
            if existing:
                if cast(GeometricConstraint, existing[0]).type is gc.type:
                    return True
                return False
            # Keep track of the added constraint for removal, i.e. take a
            # snapshot of the current domain of the vars.
            poly2domain: dict[Polygon, list[Vec2]] = {}
            for var in self.get_variables():
                poly = cast(Polygon, var)
                poly2domain[poly] = poly.get_full_space_representation()
            self._constraint_track[gc] = poly2domain
            # Adding the constraint.
            if gc.type is GeometricConstraint.Type.DC:
                from_ = gc.from_
                from_original_domain = from_.get_full_space_representation()
                self.logger.debug("added DC between Polygon %s Polygon %s", from_.id, gc.to.id)
                added = self._apply_polygon_separation(from_, gc.to)
                if self._obstacles is not None:
                    for obstacle in self._obstacles:
                        manifold = Manifold(from_, cast(Polygon, obstacle))
                        if manifold.is_collided():
                            from_.set_domain(*from_original_domain)
                            return False
                return added
            elif gc.type is GeometricConstraint.Type.INSIDE:
                if not self._apply_inside(gc.from_, gc.to):
                    return False
        return True

    def _verify_situation(self, c: Constraint) -> bool:
        gc = cast(GeometricConstraint, c)
        if gc.type is GeometricConstraint.Type.DC:
            manifold = Manifold(gc.from_, gc.to)
            if manifold.is_collided():
                return False
        elif gc.type is GeometricConstraint.Type.INSIDE:
            return self._check_inside(gc.from_, gc.to)
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        for con in c:
            gc = cast(GeometricConstraint, con)
            self.logger.debug(
                "Removed constraint between Polygon %s Polygon %s", gc.from_.id, gc.to.id
            )
            temp = self._constraint_track[gc]
            for p, domain in temp.items():
                p.set_domain(*domain)
            del self._constraint_track[gc]

    @staticmethod
    def draw_polygons(to_plots: list[list[Vec2]], horizon: int) -> str:
        ret = f"set xrange [-102:{horizon}]\n"
        ret += f"set yrange [-102:{horizon}]\n"
        for i, vector in enumerate(to_plots):
            ret += f"set obj {i + 1} polygon from "
            for k in range(len(vector) - 1):
                ret += f"{vector[k].x},{vector[k].y} to "
            ret += f"{vector[-1].x},{vector[-1].y} front fs transparent solid 0.0 border {i + 1} lw 2\n"
        ret += "plot NaN\n"
        ret += "pause -1"
        return ret

    def set_obstacles(self, variables: list[Variable]) -> None:
        self._obstacles = variables

    def get_obstacles(self) -> list[Variable] | None:
        return self._obstacles
