"""Port of spatial/geometry/Vertex.java: the Domain of a Polygon (its
vertices, in polygon-local space)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain
from metacsp.spatial.geometry.vec2 import Vec2

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["Vertex", "MAX_POLY_VERTEX_COUNT"]

MAX_POLY_VERTEX_COUNT = 260


class Vertex(Domain):
    def __init__(self, v: Variable) -> None:
        super().__init__(v)
        self.vertices: list[Vec2] = Vec2.array_of(MAX_POLY_VERTEX_COUNT)

    def compare_to(self, o: object) -> int:
        return 0

    def __str__(self) -> str:
        return "".join(f" ({v.x}, {v.y})" for v in self.vertices)

    def set_vertices(self, vertices: list[Vec2]) -> None:
        self.vertices = vertices

    def get_vertices(self) -> list[Vec2]:
        return self.vertices

    def clone(self) -> list[Vec2]:
        return [Vec2(v.x, v.y) for v in self.vertices]
