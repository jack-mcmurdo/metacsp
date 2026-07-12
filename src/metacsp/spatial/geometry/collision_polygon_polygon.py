"""Port of spatial/geometry/CollisionPolygonPolygon.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.spatial.geometry.impulse_math import ImpulseMath
from metacsp.spatial.geometry.vec2 import Vec2

if TYPE_CHECKING:
    from metacsp.spatial.geometry.manifold import Manifold
    from metacsp.spatial.geometry.polygon import Polygon

__all__ = ["CollisionPolygonPolygon"]


class CollisionPolygonPolygon:
    """Separating-axis-theorem collision detection and manifold generation
    between two convex Polygons."""

    def handle_collision(self, m: Manifold, a: Polygon, b: Polygon) -> bool:
        m.contact_count = 0

        face_a = [0]
        penetration_a = self.find_axis_least_penetration(face_a, a, b)
        if penetration_a >= 0.0:
            return False

        face_b = [0]
        penetration_b = self.find_axis_least_penetration(face_b, b, a)
        if penetration_b >= 0.0:
            return False

        # Determine which shape contains the reference face.
        if ImpulseMath.gt(penetration_a, penetration_b):
            ref_poly = a
            inc_poly = b
            a.ref = True
            b.incident = True
            reference_index = face_a[0]
            flip = False
        else:
            ref_poly = b
            inc_poly = a
            b.ref = True
            a.incident = True
            reference_index = face_b[0]
            flip = True

        incident_face = Vec2.array_of(2)
        self.find_incident_face(incident_face, ref_poly, inc_poly, reference_index)

        # Setup reference face vertices.
        assert ref_poly.domain is not None
        v1 = ref_poly.domain.vertices[reference_index]
        reference_index = 0 if reference_index + 1 == ref_poly.vertex_count else reference_index + 1
        v2 = ref_poly.domain.vertices[reference_index]

        # Transform vertices to world space.
        v1 = ref_poly.u.mul(v1).addi(ref_poly.position)
        v2 = ref_poly.u.mul(v2).addi(ref_poly.position)

        side_plane_normal = v2.sub(v1)
        side_plane_normal.normalize()

        ref_face_normal = Vec2(side_plane_normal.y, -side_plane_normal.x)

        ref_c = Vec2.dot_(ref_face_normal, v1)
        neg_side = -Vec2.dot_(side_plane_normal, v1)
        pos_side = Vec2.dot_(side_plane_normal, v2)

        if self.clip(side_plane_normal.neg(), neg_side, incident_face) < 2:
            return False
        if self.clip(side_plane_normal, pos_side, incident_face) < 2:
            return False

        m.normal.set(ref_face_normal)
        if flip:
            m.normal.negi()

        cp = 0
        separation = Vec2.dot_(ref_face_normal, incident_face[0]) - ref_c
        if separation <= 0.0:
            m.contacts[cp].set(incident_face[0])
            m.penetration = -separation
            cp += 1
        else:
            m.penetration = 0.0

        separation = Vec2.dot_(ref_face_normal, incident_face[1]) - ref_c
        if separation <= 0.0:
            m.contacts[cp].set(incident_face[1])
            m.penetration += -separation
            cp += 1
            m.penetration /= cp

        m.contact_count = cp
        return True

    def find_axis_least_penetration(self, face_index: list[int], a: Polygon, b: Polygon) -> float:
        best_distance = float("-inf")
        best_index = 0

        assert a.domain is not None
        for i in range(a.vertex_count):
            nw = a.u.mul(a.normals[i])
            bu_t = b.u.transpose()
            n = bu_t.mul(nw)

            s = b.get_support(n.neg())
            assert s is not None

            v = bu_t.muli(a.u.mul(a.domain.vertices[i]).addi(a.position).subi(b.position))
            assert v is not None

            d = Vec2.dot_(n, s.sub(v))

            if d > best_distance:
                best_distance = d
                best_index = i

        face_index[0] = best_index
        return best_distance

    def find_incident_face(
        self, v: list[Vec2], ref_poly: Polygon, inc_poly: Polygon, reference_index: int
    ) -> None:
        reference_normal = ref_poly.normals[reference_index]

        reference_normal = ref_poly.u.mul(reference_normal)  # To world space
        reference_normal = inc_poly.u.transpose().mul(reference_normal)  # To incident's model space

        incident_face = 0
        min_dot = float("inf")
        for i in range(inc_poly.vertex_count):
            dot = Vec2.dot_(reference_normal, inc_poly.normals[i])
            if dot < min_dot:
                min_dot = dot
                incident_face = i

        assert inc_poly.domain is not None
        v[0] = inc_poly.u.mul(inc_poly.domain.vertices[incident_face]).addi(inc_poly.position)
        incident_face = 0 if incident_face + 1 >= inc_poly.vertex_count else incident_face + 1
        v[1] = inc_poly.u.mul(inc_poly.domain.vertices[incident_face]).addi(inc_poly.position)

    def clip(self, n: Vec2, c: float, face: list[Vec2]) -> int:
        sp = 0
        out = [Vec2(face[0].x, face[0].y), Vec2(face[1].x, face[1].y)]

        d1 = Vec2.dot_(n, face[0]) - c
        d2 = Vec2.dot_(n, face[1]) - c

        if d1 <= 0.0:
            out[sp].set(face[0])
            sp += 1
        if d2 <= 0.0:
            out[sp].set(face[1])
            sp += 1

        if d1 * d2 < 0.0:
            alpha = d1 / (d1 - d2)
            out[sp].set(face[1]).subi(face[0]).muli(alpha).addi(face[0])
            sp += 1

        face[0] = out[0]
        face[1] = out[1]

        return sp

    def verify_collision(self, m: Manifold, a: Polygon, b: Polygon) -> bool:
        m.contact_count = 0

        face_a = [0]
        penetration_a = self.find_axis_least_penetration(face_a, a, b)
        if penetration_a >= 0.0:
            return False

        face_b = [0]
        penetration_b = self.find_axis_least_penetration(face_b, b, a)
        if penetration_b >= 0.0:
            return False

        return True
