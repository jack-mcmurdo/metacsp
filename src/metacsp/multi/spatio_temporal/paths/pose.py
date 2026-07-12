"""Port of multi/spatioTemporal/paths/Pose.java."""

from __future__ import annotations

import math
from typing import Union

__all__ = ["Pose"]

# A JTS Coordinate maps to a plain tuple (D4); Pose.position is 2D for 2D
# poses and 3D for 3D poses, mirroring the two Coordinate constructors used
# by Pose.getPosition().
Coordinate2D = tuple[float, float]
Coordinate3D = tuple[float, float, float]


def _coordinate_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """2D Euclidean distance, matching JTS ``Coordinate.distance()`` which
    (perhaps surprisingly) only ever considers x and y, even for 3D
    coordinates."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def _hash_component(value: float) -> float:
    """Java's ``hashCode()`` zeroes out NaN components (roll, pitch, z) before
    hashing; the exact ``Double.doubleToLongBits``-based accumulation isn't
    reproduced (not observable/testable from Python), but the same
    NaN-zeroing structure is."""
    return 0.0 if math.isnan(value) else value


class Pose:
    """The pose of a robot in 2D or 3D.

    Mirrors the two Java constructors: ``Pose(x, y, z, roll, pitch, yaw)``
    for 3D poses and ``Pose(x, y, theta)`` for 2D poses (collapsed into one
    Python constructor dispatching on argument count, since Python has no
    method overloading).
    """

    def __init__(
        self,
        x: float,
        y: float,
        z_or_theta: float,
        roll: float | None = None,
        pitch: float | None = None,
        yaw: float | None = None,
    ) -> None:
        if roll is None and pitch is None and yaw is None:
            # Pose(x, y, theta) -- 2D pose.
            self.x = x
            self.y = y
            self.yaw = z_or_theta
            self.z = math.nan
            self.roll = math.nan
            self.pitch = math.nan
        else:
            if roll is None or pitch is None or yaw is None:
                raise TypeError("Pose() takes (x, y, theta) or (x, y, z, roll, pitch, yaw)")
            # Pose(x, y, z, roll, pitch, yaw) -- 3D pose.
            self.x = x
            self.y = y
            self.z = z_or_theta
            self.roll = roll
            self.pitch = pitch
            self.yaw = yaw

    @property
    def theta(self) -> float:
        """Same as :attr:`yaw`."""
        return self.yaw

    @property
    def position(self) -> Union[Coordinate2D, Coordinate3D]:
        """This pose's (x, y) or (x, y, z) coordinate, depending on dimensionality."""
        if math.isnan(self.z):
            return (self.x, self.y)
        return (self.x, self.y, self.z)

    def distance_to(self, p: Pose) -> float:
        """2D Euclidean distance between this pose and ``p``."""
        return _coordinate_distance(p.position, self.position)

    @staticmethod
    def lerp(a: float, b: float, ratio: float) -> float:
        """Linear interpolation between ``a`` and ``b`` at the given ratio in [0, 1]."""
        return (a * (1.0 - ratio)) + (b * ratio)

    @staticmethod
    def lerp_degrees(a: float, b: float, ratio: float) -> float:
        """Linear interpolation between two angles (radians), taking the shorter arc."""
        difference = abs(b - a)
        if difference > math.pi:
            if b > a:
                a += 2 * math.pi
            else:
                b += 2 * math.pi
        value = (a * (1.0 - ratio)) + (b * ratio)
        range_zero = 2 * math.pi
        if 0 <= value <= 2 * math.pi:
            return value
        return math.fmod(value, range_zero)

    def interpolate(self, p2: Pose, ratio: float) -> Pose:
        """Linearly interpolate between this pose and ``p2`` at the given ratio in [0, 1]."""
        new_x = Pose.lerp(self.x, p2.x, ratio)
        new_y = Pose.lerp(self.y, p2.y, ratio)
        if math.isnan(self.z):
            new_theta = Pose.lerp_degrees(self.theta, p2.theta, ratio)
            return Pose(new_x, new_y, new_theta)
        new_z = Pose.lerp(self.z, p2.z, ratio)
        new_roll = Pose.lerp_degrees(self.roll, p2.roll, ratio)
        new_pitch = Pose.lerp_degrees(self.pitch, p2.pitch, ratio)
        new_yaw = Pose.lerp_degrees(self.yaw, p2.yaw, ratio)
        return Pose(new_x, new_y, new_z, new_roll, new_pitch, new_yaw)

    def __str__(self) -> str:
        if math.isnan(self.z):
            return f"({self.x:.4f}, {self.y:.4f}, {self.theta:.4f})"
        return (
            f"({self.x:.4f}, {self.y:.4f}, {self.z:.4f}, "
            f"{self.roll:.4f}, {self.pitch:.4f}, {self.yaw:.4f})"
        )

    def __hash__(self) -> int:
        return hash(
            (
                _hash_component(self.pitch),
                _hash_component(self.roll),
                self.x,
                self.y,
                self.yaw,
                _hash_component(self.z),
            )
        )

    @property
    def is_pose2d(self) -> bool:
        """True iff this pose was constructed with only (x, y, theta)."""
        return math.isnan(self.roll) or math.isnan(self.pitch) or math.isnan(self.z)

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Pose) or type(other) is not type(self):
            return False

        if (self.is_pose2d and not other.is_pose2d) or (not self.is_pose2d and other.is_pose2d):
            raise RuntimeError("Invalid comparison between a 2D pose and a 3D one.")

        # Compare the two 2D poses.
        if self.x != other.x:
            return False
        if self.y != other.y:
            return False
        if self.yaw != other.yaw:
            return False
        if self.is_pose2d and other.is_pose2d:
            return True

        # Compare the two 3D poses.
        if (
            math.isnan(self.roll)
            or math.isnan(self.pitch)
            or math.isnan(self.z)
            or math.isnan(other.roll)
            or math.isnan(other.pitch)
            or math.isnan(other.z)
        ):
            raise RuntimeError("Invalid 3D poses.")

        if self.z != other.z:
            return False
        if self.pitch != other.pitch:
            return False
        if self.roll != other.roll:
            return False
        return True
