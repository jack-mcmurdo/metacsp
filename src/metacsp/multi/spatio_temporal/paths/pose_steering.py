"""Port of multi/spatioTemporal/paths/PoseSteering.java."""

from __future__ import annotations

from typing import Union

from metacsp.multi.spatio_temporal.paths.pose import Pose

__all__ = ["PoseSteering"]


class PoseSteering:
    """A :class:`Pose` plus a steering angle.

    Mirrors the three Java constructors: ``PoseSteering(x, y, z, roll,
    pitch, yaw, steering)``, ``PoseSteering(x, y, theta, steering)``, and
    ``PoseSteering(Pose p, steering)`` (collapsed into one Python
    constructor dispatching on argument count/type, since Python has no
    method overloading).
    """

    def __init__(self, *args: Union[float, Pose]) -> None:
        if len(args) == 7:
            x, y, z, roll, pitch, yaw, steering = args  # type: ignore[misc]
            self.pose = Pose(x, y, z, roll, pitch, yaw)  # type: ignore[arg-type]
            self.steering = steering
        elif len(args) == 4:
            x, y, theta, steering = args  # type: ignore[misc]
            self.pose = Pose(x, y, theta)  # type: ignore[arg-type]
            self.steering = steering
        elif len(args) == 2 and isinstance(args[0], Pose):
            p, steering = args
            self.pose = p
            self.steering = steering  # type: ignore[assignment]
        else:
            raise TypeError(
                "PoseSteering() takes (x, y, z, roll, pitch, yaw, steering), "
                "(x, y, theta, steering), or (Pose, steering)"
            )

    def __str__(self) -> str:
        return f"PoseSteering [pose={self.pose}, steering={self.steering}]"

    @property
    def x(self) -> float:
        return self.pose.x

    @property
    def y(self) -> float:
        return self.pose.y

    @property
    def z(self) -> float:
        return self.pose.z

    @property
    def theta(self) -> float:
        return self.pose.theta

    @property
    def roll(self) -> float:
        return self.pose.roll

    @property
    def pitch(self) -> float:
        return self.pose.pitch

    @property
    def yaw(self) -> float:
        return self.pose.yaw

    def interpolate(self, p2: PoseSteering, ratio: float) -> PoseSteering:
        interp = self.pose.interpolate(p2.pose, ratio)
        return PoseSteering(interp, Pose.lerp_degrees(self.steering, p2.steering, ratio))

    def __hash__(self) -> int:
        return hash((self.pose, self.steering))

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, PoseSteering) or type(other) is not type(self):
            return False
        if self.pose != other.pose:
            return False
        return self.steering == other.steering
