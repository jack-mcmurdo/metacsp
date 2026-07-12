"""Port of spatial/geometry/Polygon.java.

The gift-wrapping (convex hull) computation is factored into a single
``_convex_hull_order`` helper shared by ``order_vertex``/``set`` (which are
byte-for-byte identical in the Java source save for what each does with the
result).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from metacsp.framework.variable import Variable
from metacsp.spatial.geometry.mat2 import Mat2
from metacsp.spatial.geometry.vec2 import Vec2
from metacsp.spatial.geometry.vertex import MAX_POLY_VERTEX_COUNT, Vertex

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain

__all__ = ["Polygon"]

# Min/max dimensions of the Euclidean space (mirrored from
# GeometricConstraintSolver, which Polygon depends on for its initial/default
# domain -- defined here instead to avoid a module cycle; re-exposed as class
# attributes on GeometricConstraintSolver for call-site fidelity).
MAX_X = 10000.0
MAX_Y = 10000.0
MIN_X = -10000.0
MIN_Y = -10000.0


def _convex_hull_order(verts: list[Vec2]) -> tuple[list[Vec2], int]:
    """Order ``verts`` counter-clockwise around their convex hull (gift
    wrapping). Returns a MAX_POLY_VERTEX_COUNT-capacity array (as Java does)
    with the first ``vertex_count`` entries populated, and that count."""
    vertices = Vec2.array_of(MAX_POLY_VERTEX_COUNT)

    right_most = 0
    highest_x_coord = verts[0].x
    for i in range(1, len(verts)):
        x = verts[i].x
        if x > highest_x_coord:
            highest_x_coord = x
            right_most = i
        elif x == highest_x_coord:
            if verts[i].y < verts[right_most].y:
                right_most = i

    hull = [0] * MAX_POLY_VERTEX_COUNT
    out_count = 0
    index_hull = right_most

    while True:
        hull[out_count] = index_hull
        next_hull_index = 0
        for i in range(1, len(verts)):
            if next_hull_index == index_hull:
                next_hull_index = i
                continue
            e1 = verts[next_hull_index].sub(verts[hull[out_count]])
            e2 = verts[i].sub(verts[hull[out_count]])
            c = Vec2.cross_(e1, e2)
            if c < 0.0:
                next_hull_index = i
            if c == 0.0 and e2.length_sq() > e1.length_sq():
                next_hull_index = i

        out_count += 1
        index_hull = next_hull_index

        if next_hull_index == right_most:
            vertex_count = out_count
            break

    for i in range(vertex_count):
        vertices[i].set(verts[hull[i]])

    return vertices, vertex_count


class Polygon(Variable):
    """A convex polygon Variable used by the physics-based geometric constraint solvers."""

    MAX_POLY_VERTEX_COUNT = MAX_POLY_VERTEX_COUNT

    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._dom: Vertex | None = None
        self.vertex_count = 0
        self.is_movable = True
        self.normals: list[Vec2] = Vec2.array_of(MAX_POLY_VERTEX_COUNT)
        self.u = Mat2()
        self._position = Vec2()
        self.ref = False
        self.incident = False
        self.has_default_domain = True
        self.orientation = 0.0
        self._set_initial_domain()

    def set_movable(self, is_movable: bool) -> None:
        self.is_movable = is_movable

    @property
    def domain(self) -> Domain | None:
        return self._dom

    @domain.setter
    def domain(self, d: Any) -> None:
        pass

    def set_domain(self, *verts: Vec2) -> None:
        self._dom = Vertex(self)
        self.vertex_count = len(verts)
        self._set_orient(0.0)
        centroid = self._get_centroid(*self._order_vertex(*verts))
        self.position.set(centroid.x, centroid.y)
        half_poly = [Vec2(v.x - self.position.x, v.y - self.position.y) for v in verts]
        self._set(*half_poly)
        self._initialize()
        self.has_default_domain = False

    def _set_initial_domain(self) -> None:
        p1 = Vec2(MIN_X, MAX_Y)
        p2 = Vec2(MAX_X, MAX_Y)
        p3 = Vec2(MAX_X, MIN_Y)
        p4 = Vec2(MIN_X, MIN_Y)
        self.set_domain(p1, p2, p3, p4)
        self.has_default_domain = True

    def __str__(self) -> str:
        ret = f"{type(self).__name__} {self.id}"
        dom = self._dom
        assert dom is not None
        for i in range(self.vertex_count):
            ret += f" {dom.vertices[i]}"
        return ret

    def _initialize(self) -> None:
        self._compute_mass(1.0)

    def _compute_mass(self, density: float) -> None:
        # Calculate centroid and moment of inertia.
        area = 0.0
        k_inv3 = 1.0 / 3.0
        c = Vec2(0.0, 0.0)

        assert self._dom is not None
        for i in range(self.vertex_count):
            p1 = self._dom.vertices[i]
            p2 = self._dom.vertices[(i + 1) % self.vertex_count]

            d = Vec2.cross_(p1, p2)
            triangle_area = 0.5 * d
            area += triangle_area

            weight = triangle_area * k_inv3
            c.addsi(p1, weight)
            c.addsi(p2, weight)

        c.muli(1.0 / area)

        for i in range(self.vertex_count):
            self._dom.vertices[i].subi(c)

    def _get_centroid(self, *vers: Vec2) -> Vec2:
        vertices_copy = [Vec2(v.x, v.y) for v in vers]

        area = 0.0
        k_inv3 = 1.0 / 3.0
        c = Vec2(0.0, 0.0)

        for i in range(self.vertex_count):
            p1 = vertices_copy[i]
            p2 = vertices_copy[(i + 1) % self.vertex_count]

            d = Vec2.cross_(p1, p2)
            triangle_area = 0.5 * d
            area += triangle_area

            weight = triangle_area * k_inv3
            c.addsi(p1, weight)
            c.addsi(p2, weight)

        c.muli(1.0 / area)

        for i in range(self.vertex_count):
            vertices_copy[i].subi(c)
        return c

    def get_orientation(self) -> float:
        return self.orientation

    def set_orientation(self, orientation: float) -> None:
        self.orientation = orientation

    def _set_orient(self, radians: float) -> None:
        self.u.set(radians)

    def _order_vertex(self, *verts: Vec2) -> list[Vec2]:
        vertices, vertex_count = _convex_hull_order(list(verts))
        self.vertex_count = vertex_count
        return vertices

    def _set(self, *verts: Vec2) -> None:
        vertices, vertex_count = _convex_hull_order(list(verts))
        self.vertex_count = vertex_count

        for i in range(self.vertex_count):
            face = vertices[(i + 1) % self.vertex_count].sub(vertices[i])
            self.normals[i].set(face.y, -face.x)
            self.normals[i].normalize()
        assert self._dom is not None
        self._dom.set_vertices(vertices)

    def get_support(self, direction: Vec2) -> Vec2 | None:
        best_projection = float("-inf")
        best_vertex: Vec2 | None = None
        assert self._dom is not None
        for i in range(self.vertex_count):
            v = self._dom.vertices[i]
            projection = Vec2.dot_(v, direction)
            if projection > best_projection:
                best_vertex = v
                best_projection = projection
        return best_vertex

    @property
    def position(self) -> Vec2:
        return self._position

    @position.setter
    def position(self, position: Vec2) -> None:
        self._position = position

    def get_full_space_representation(self) -> list[Vec2]:
        vecs: list[Vec2] = []
        assert self._dom is not None
        for i in range(self.vertex_count):
            v = Vec2(self._dom.vertices[i].x, self._dom.vertices[i].y)
            self.u.muli(v)
            v.addi(self.position)
            vecs.append(v)
        return vecs

    def __lt__(self, other: Variable) -> bool:
        return False
