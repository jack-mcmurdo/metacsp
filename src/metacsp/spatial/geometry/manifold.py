"""Port of spatial/geometry/Manifold.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.spatial.geometry.collision_polygon_polygon import CollisionPolygonPolygon
from metacsp.spatial.geometry.vec2 import Vec2

if TYPE_CHECKING:
    from metacsp.spatial.geometry.polygon import Polygon

__all__ = ["Manifold"]


class Manifold:
    """The contact information (normal, penetration, contact points) resulting
    from a collision test between two Polygons."""

    def __init__(self, a: Polygon, b: Polygon) -> None:
        self.a = a
        self.b = b
        self.penetration = 0.0
        self.normal = Vec2()
        self.contacts = [Vec2(), Vec2()]
        self.contact_count = 0

    def solve(self) -> bool:
        cpp = CollisionPolygonPolygon()
        return cpp.handle_collision(self, self.a, self.b)

    def is_collided(self) -> bool:
        return CollisionPolygonPolygon().verify_collision(self, self.a, self.b)

    def positional_correction(self) -> None:
        correction = self.penetration
        self.a.position.addsi(self.normal, -(correction * 1.1))
