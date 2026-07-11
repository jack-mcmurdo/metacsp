"""Port of tests/TestBounds.java."""

from __future__ import annotations

from metacsp.time import Bounds


class TestBounds:
    def test_intersection(self):
        b1 = Bounds(0, 10)
        b2 = Bounds(5, 10)

        i1 = b1.intersect_strict(b2)
        i2 = b2.intersect_strict(b1)

        assert i1.min == 5 and i1.max == 10
        assert i2.min == 5 and i2.max == 10

        assert b1.intersect(b1) == b1
        assert b2.intersect(b2) == b2

    def test_empty_intersection(self):
        b1 = Bounds(0, 4)
        b2 = Bounds(5, 10)

        assert b1.intersect_strict(b2) is None
        assert b2.intersect_strict(b1) is None

    def test_meets_intersection(self):
        b1 = Bounds(0, 5)
        b2 = Bounds(5, 10)

        assert b1.intersect_strict(b2) is None
        assert b2.intersect_strict(b1) is None
