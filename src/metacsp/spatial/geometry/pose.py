"""Port of spatial/geometry/Pose.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.spatial.geometry.position import Position
    from metacsp.spatial.geometry.quaternion import Quaternion

__all__ = ["Pose"]


class Pose:
    def __init__(self) -> None:
        self.position: Position | None = None
        self.orientation: Quaternion | None = None
