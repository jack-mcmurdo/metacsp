"""Port of spatial/geometry/Quaternion.java."""

from __future__ import annotations

__all__ = ["Quaternion"]


class Quaternion:
    def __init__(self, x: float, y: float, z: float, w: float) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.w = w
