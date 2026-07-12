"""Port of spatial/geometry/ImpulseMath.java."""

from __future__ import annotations

import math
import random

from metacsp.spatial.geometry.vec2 import Vec2

__all__ = ["ImpulseMath"]


class ImpulseMath:
    PI = math.pi
    EPSILON = 0.0001
    EPSILON_SQ = EPSILON * EPSILON
    BIAS_RELATIVE = 0.95
    BIAS_ABSOLUTE = 0.01
    DT = 1.0 / 60.0
    GRAVITY = Vec2(0.0, 50.0)
    PENETRATION_ALLOWANCE = 0.0
    PENETRATION_CORRETION = 0.0

    @staticmethod
    def equal(a: float, b: float) -> bool:
        return abs(a - b) <= ImpulseMath.EPSILON

    @staticmethod
    def clamp(min_: float, max_: float, a: float) -> float:
        return min_ if a < min_ else (max_ if a > max_ else a)

    @staticmethod
    def round(a: float) -> int:
        return int(a + 0.5)

    @staticmethod
    def random(min_: float, max_: float) -> float:
        return (max_ - min_) * random.random() + min_

    @staticmethod
    def gt(a: float, b: float) -> bool:
        return a >= b * ImpulseMath.BIAS_RELATIVE + a * ImpulseMath.BIAS_ABSOLUTE
