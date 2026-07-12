"""Port of spatial/geometry/Mat2.java: a 2x2 transformation matrix."""

from __future__ import annotations

import math

from metacsp.spatial.geometry.vec2 import Vec2

__all__ = ["Mat2"]


class Mat2:
    def __init__(self, *args: float) -> None:
        self.m00 = self.m01 = self.m10 = self.m11 = 0.0
        if len(args) == 1:
            self.set(args[0])
        elif len(args) == 4:
            self.set(*args)

    def set(self, *args: float | Mat2) -> None:
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, Mat2):
                self.m00, self.m01, self.m10, self.m11 = arg.m00, arg.m01, arg.m10, arg.m11
            else:
                radians = arg
                c = math.cos(radians)
                s = math.sin(radians)
                self.m00 = c
                self.m01 = -s
                self.m10 = s
                self.m11 = c
        elif len(args) == 4:
            a, b, c, d = args
            self.m00, self.m01, self.m10, self.m11 = a, b, c, d

    def absi(self) -> None:
        self.abs(self)

    def abs(self, out: Mat2 | None = None) -> Mat2:
        out = out if out is not None else Mat2()
        out.m00 = abs(self.m00)
        out.m01 = abs(self.m01)
        out.m10 = abs(self.m10)
        out.m11 = abs(self.m11)
        return out

    def get_axis_x(self, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = self.m00
        out.y = self.m10
        return out

    def get_axis_y(self, out: Vec2 | None = None) -> Vec2:
        out = out if out is not None else Vec2()
        out.x = self.m01
        out.y = self.m11
        return out

    def transposei(self) -> None:
        self.m01, self.m10 = self.m10, self.m01

    def transpose(self, out: Mat2 | None = None) -> Mat2:
        out = out if out is not None else Mat2()
        out.m00 = self.m00
        out.m01 = self.m10
        out.m10 = self.m01
        out.m11 = self.m11
        return out

    def muli(self, v: Vec2 | Mat2) -> Vec2 | None:
        if isinstance(v, Vec2):
            return self.mul(v.x, v.y, v)
        self.set(
            self.m00 * v.m00 + self.m01 * v.m10,
            self.m00 * v.m01 + self.m01 * v.m11,
            self.m10 * v.m00 + self.m11 * v.m10,
            self.m10 * v.m01 + self.m11 * v.m11,
        )
        return None

    def mul(
        self, x: float | Vec2 | Mat2, y: float | Vec2 | None = None, out: Vec2 | None = None
    ) -> Vec2 | Mat2:
        if isinstance(x, Mat2):
            out_mat = y if isinstance(y, Mat2) else Mat2()
            out_mat.m00 = self.m00 * x.m00 + self.m01 * x.m10
            out_mat.m01 = self.m00 * x.m01 + self.m01 * x.m11
            out_mat.m10 = self.m10 * x.m00 + self.m11 * x.m10
            out_mat.m11 = self.m10 * x.m01 + self.m11 * x.m11
            return out_mat
        if isinstance(x, Vec2):
            out_vec = y if isinstance(y, Vec2) else Vec2()
            return self.mul(x.x, x.y, out_vec)
        out_vec = out if out is not None else Vec2()
        assert y is not None and not isinstance(y, Vec2)
        out_vec.x = self.m00 * x + self.m01 * y
        out_vec.y = self.m10 * x + self.m11 * y
        return out_vec
