"""Port of spatial/geometry/Pose.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.spatial.geometry.position import Position
    from metacsp.spatial.geometry.quaternion import Quaternion

__all__ = ["Pose"]


class Pose:
    """A 2D position plus orientation, used by the geometry package's physics types."""

    def __init__(self) -> None:
        self.position: Position | None = None
        self.orientation: Quaternion | None = None
