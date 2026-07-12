"""Port of spatial/geometry/Quaternion.java."""

from __future__ import annotations

__all__ = ["Quaternion"]


class Quaternion:
    """An (x, y, z, w) quaternion representing an orientation, used by the geometry package."""

    def __init__(self, x: float, y: float, z: float, w: float) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.w = w
