"""Port of multi/spatioTemporal/paths/Quaternion.java.

Not to be confused with ``metacsp.spatial.geometry.Quaternion`` (M10, ported
from a *different* Java class of the same simple name in package
``org.metacsp.spatial.geometry``). This is the distinct class from package
``org.metacsp.multi.spatioTemporal.paths``, kept in its own module per the
module map.
"""

from __future__ import annotations

import math

__all__ = ["Quaternion"]


class Quaternion:
    """Maintains and converts to/from quaternion representations.

    Mirrors the three Java constructors: ``Quaternion(x, y, z, w)``,
    ``Quaternion(roll, pitch, yaw)``, and ``Quaternion(theta)`` (collapsed
    into one Python constructor dispatching on argument count, since Python
    has no method overloading).
    """

    def __init__(self, *args: float) -> None:
        if len(args) == 4:
            self.x, self.y, self.z, self.w = args
        elif len(args) == 3:
            roll, pitch, yaw = args
            cy = math.cos(yaw * 0.5)
            sy = math.sin(yaw * 0.5)
            cr = math.cos(roll * 0.5)
            sr = math.sin(roll * 0.5)
            cp = math.cos(pitch * 0.5)
            sp = math.sin(pitch * 0.5)

            self.w = cy * cr * cp + sy * sr * sp
            self.x = cy * sr * cp - sy * cr * sp
            self.y = cy * cr * sp + sy * sr * cp
            self.z = sy * cr * cp - cy * sr * sp
        elif len(args) == 1:
            (theta,) = args
            self.x = 0.0
            self.y = 0.0
            self.z = math.sin(theta / 2.0)
            self.w = math.cos(theta / 2.0)
        else:
            raise TypeError("Quaternion() takes (x, y, z, w), (roll, pitch, yaw), or (theta,)")

    @property
    def roll_pitch_yaw(self) -> tuple[float, float, float]:
        """The roll, pitch and yaw angles in radians represented by this
        Quaternion."""
        # roll (x-axis rotation)
        sinr = 2.0 * (self.w * self.x + self.y * self.z)
        cosr = 1.0 - 2.0 * (self.x * self.x + self.y * self.y)
        roll = math.atan2(sinr, cosr)

        # pitch (y-axis rotation)
        sinp = 2.0 * (self.w * self.y - self.z * self.x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2.0, sinp)
        else:
            pitch = math.asin(sinp)

        # yaw (z-axis rotation)
        siny = 2.0 * (self.w * self.z + self.x * self.y)
        cosy = 1.0 - 2.0 * (self.y * self.y + self.z * self.z)
        yaw = math.atan2(siny, cosy)

        return (roll, pitch, yaw)

    @property
    def theta(self) -> float:
        """The angle in radians represented by this Quaternion."""
        return self.roll_pitch_yaw[2]

    def norm(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w)

    def conjugate(self) -> Quaternion:
        return Quaternion(self.x, -self.y, -self.z, -self.w)

    def plus(self, other: Quaternion) -> Quaternion:
        return Quaternion(self.x + other.x, self.y + other.y, self.z + other.z, self.w + other.w)

    def times(self, other: Quaternion) -> Quaternion:
        x = self.x * other.x - self.y * other.y - self.z * other.z - self.w * other.w
        y = self.x * other.y + self.y * other.x + self.z * other.w - self.w * other.z
        z = self.x * other.z - self.y * other.w + self.z * other.x + self.w * other.y
        w = self.x * other.w + self.y * other.z - self.z * other.y + self.w * other.x
        return Quaternion(x, y, z, w)

    def inverse(self) -> Quaternion:
        d = self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w
        return Quaternion(self.x / d, -self.y / d, -self.z / d, -self.w / d)

    def divide(self, other: Quaternion) -> Quaternion:
        return self.times(other.inverse())

    def __str__(self) -> str:
        return f"{self.x} + {self.y}i + {self.z}j + {self.w}k"
