"""Port of spatial/geometry/SutherlandHodgman.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.spatial.geometry.vec2 import Vec2

if TYPE_CHECKING:
    from metacsp.spatial.geometry.polygon import Polygon

__all__ = ["SutherlandHodgman"]


class SutherlandHodgman:
    """Clips ``p2`` (the subject) against ``p1`` (the clipper)."""

    def __init__(self, p1: Polygon, p2: Polygon) -> None:
        self.pol: list[Vec2] = []

        p1vec = p1.get_full_space_representation()
        clip_points: list[tuple[float, float]] = []
        for v in p1vec:
            clip_points.append((v.x, v.y))
            self.pol.append(Vec2(v.x, v.y))

        p2vec = p2.get_full_space_representation()
        subj_points = [(v.x, v.y) for v in p2vec]

        self.subject: list[tuple[float, float]] = list(subj_points)
        self.result: list[tuple[float, float]] = list(self.subject)
        self.clipper: list[tuple[float, float]] = list(clip_points)

        self._clip_polygon()

    def get_clipped_result(self) -> list[Vec2]:
        return [Vec2(p[0], p[1]) for p in self.result]

    def get_contact_points(self) -> list[Vec2]:
        ret: list[Vec2] = []
        epsilon = 0.003
        clipped = self.get_clipped_result()
        for point in clipped:
            found = False
            for p in self.pol:
                if abs(p.x - point.x) < epsilon and abs(p.y - point.y) < epsilon:
                    found = True
            if not found:
                ret.append(point)
        return ret

    def _clip_polygon(self) -> None:
        length = len(self.clipper)
        for i in range(length):
            length2 = len(self.result)
            input_ = self.result
            self.result = []

            a = self.clipper[(i + length - 1) % length]
            b = self.clipper[i]

            for j in range(length2):
                p = input_[(j + length2 - 1) % length2]
                q = input_[j]

                if self._is_inside(a, b, q):
                    if not self._is_inside(a, b, p):
                        self.result.append(self._intersection(a, b, p, q))
                    self.result.append(q)
                elif self._is_inside(a, b, p):
                    self.result.append(self._intersection(a, b, p, q))

    def _is_inside(
        self, a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
    ) -> bool:
        return (a[0] - c[0]) * (b[1] - c[1]) > (a[1] - c[1]) * (b[0] - c[0])

    def _intersection(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        p: tuple[float, float],
        q: tuple[float, float],
    ) -> tuple[float, float]:
        a1 = b[1] - a[1]
        b1 = a[0] - b[0]
        c1 = a1 * a[0] + b1 * a[1]

        a2 = q[1] - p[1]
        b2 = p[0] - q[0]
        c2 = a2 * p[0] + b2 * p[1]

        det = a1 * b2 - a2 * b1
        x = (b2 * c1 - b1 * c2) / det
        y = (a1 * c2 - a2 * c1) / det

        return (x, y)
