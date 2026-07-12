"""Port of spatial/geometry/Vec2.java.

A mutable 2D vector. Java's ``out``-parameter overloads (e.g. ``mul(s, out)``)
are kept alongside the mutating (``muli``) and allocating (``mul``) forms for
fidelity, since the physics-engine code in this package relies on all three
styles for performance.
"""

from __future__ import annotations

import math

__all__ = ["Vec2"]

EPSILON = 0.0001
EPSILON_SQ = EPSILON * EPSILON


class Vec2:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def set(self, x: float | Vec2, y: float | None = None) -> Vec2:
        if isinstance(x, Vec2):
            self.x = x.x
            self.y = x.y
        else:
            assert y is not None
            self.x = x
            self.y = y
        return self

    def negi(self) -> Vec2:
        return self.neg(self)

    def neg(self, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = -self.x
        out.y = -self.y
        return out

    def muli(self, s: float | Vec2) -> Vec2:
        return self.mul(s, self)

    def mul(self, s: float | Vec2, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        if isinstance(s, Vec2):
            out.x = self.x * s.x
            out.y = self.y * s.y
        else:
            out.x = s * self.x
            out.y = s * self.y
        return out

    def divi(self, s: float | Vec2) -> Vec2:
        return self.div(s, self)

    def div(self, s: float | Vec2, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        if isinstance(s, Vec2):
            out.x = self.x / s.x
            out.y = self.y / s.y
        else:
            out.x = self.x / s
            out.y = self.y / s
        return out

    def addi(self, v: float | Vec2) -> Vec2:
        return self.add(v, self)

    def add(self, v: float | Vec2, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        if isinstance(v, Vec2):
            out.x = self.x + v.x
            out.y = self.y + v.y
        else:
            out.x = self.x + v
            out.y = self.y + v
        return out

    def addsi(self, v: Vec2, s: float) -> Vec2:
        return self.adds(v, s, self)

    def adds(self, v: Vec2, s: float, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = self.x + v.x * s
        out.y = self.y + v.y * s
        return out

    def subi(self, v: Vec2) -> Vec2:
        return self.sub(v, self)

    def sub(self, v: Vec2, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = self.x - v.x
        out.y = self.y - v.y
        return out

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def rotate(self, radians: float) -> None:
        c = math.cos(radians)
        s = math.sin(radians)
        xp = self.x * c - self.y * s
        yp = self.x * s + self.y * c
        self.x = xp
        self.y = yp

    def normalize(self) -> None:
        len_sq = self.length_sq()
        if len_sq > EPSILON_SQ:
            inv_len = 1.0 / math.sqrt(len_sq)
            self.x *= inv_len
            self.y *= inv_len

    def mini(self, a: Vec2, b: Vec2) -> Vec2:
        return Vec2.min(a, b, self)

    def maxi(self, a: Vec2, b: Vec2) -> Vec2:
        return Vec2.max(a, b, self)

    def dot(self, v: Vec2) -> float:
        return Vec2.dot_(self, v)

    def distance_sq(self, v: Vec2) -> float:
        return Vec2.distance_sq_(self, v)

    def distance(self, v: Vec2) -> float:
        return Vec2.distance_(self, v)

    def cross(self, arg1: Vec2 | float, arg2: Vec2 | float | None = None) -> Vec2 | float:
        """Overloaded to match Java: ``cross(v, a)``/``cross(a, v)`` set self
        to the vector cross of a Vec2 and a scalar (and return self); the
        single-argument ``cross(v)`` returns the scalar cross of self and v."""
        if arg2 is None:
            assert isinstance(arg1, Vec2)
            return Vec2.cross_(self, arg1)
        if isinstance(arg1, Vec2):
            return Vec2.cross_vec_scalar(arg1, arg2, self)  # type: ignore[arg-type]
        return Vec2.cross_scalar_vec(arg1, arg2, self)  # type: ignore[arg-type]

    @staticmethod
    def min(a: Vec2, b: Vec2, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = min(a.x, b.x)
        out.y = min(a.y, b.y)
        return out

    @staticmethod
    def max(a: Vec2, b: Vec2, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = max(a.x, b.x)
        out.y = max(a.y, b.y)
        return out

    @staticmethod
    def dot_(a: Vec2, b: Vec2) -> float:
        return a.x * b.x + a.y * b.y

    @staticmethod
    def distance_sq_(a: Vec2, b: Vec2) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        return dx * dx + dy * dy

    @staticmethod
    def distance_(a: Vec2, b: Vec2) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def cross_vec_scalar(v: Vec2, a: float, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = v.y * a
        out.y = v.x * -a
        return out

    @staticmethod
    def cross_scalar_vec(a: float, v: Vec2, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = v.y * -a
        out.y = v.x * a
        return out

    @staticmethod
    def cross_(a: Vec2, b: Vec2) -> float:
        return a.x * b.y - a.y * b.x

    @staticmethod
    def array_of(length: int) -> list[Vec2]:
        return [Vec2() for _ in range(length)]

    def __str__(self) -> str:
        return f"[{self.x}, {self.y}]"

    __repr__ = __str__
