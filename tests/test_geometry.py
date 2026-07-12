"""Tests for metacsp.spatial.geometry.

There is no Java JUnit test for this package (org.metacsp.spatial.geometry
has no src/test counterpart); the fixtures below are the polygon layouts
used by examples/TestGeometricConstraintSolver{,2}.java and
examples/TestRCC2ConstraintSolver.java, asserting the same
add_constraint results those examples print.
"""

from __future__ import annotations

from metacsp.spatial.geometry import (
    GeometricConstraint,
    GeometricConstraintSolver,
    Manifold,
    Polygon,
    RCC2ConstraintSolver,
    SutherlandHodgman,
    Vec2,
)

Type = GeometricConstraint.Type


class TestVec2:
    def test_cross_scalar(self):
        a = Vec2(1.0, 2.0)
        b = Vec2(3.0, 4.0)
        assert Vec2.cross_(a, b) == 1.0 * 4.0 - 2.0 * 3.0

    def test_normalize(self):
        v = Vec2(3.0, 4.0)
        v.normalize()
        assert abs(v.length() - 1.0) < 1e-9

    def test_dot(self):
        assert Vec2.dot_(Vec2(1.0, 0.0), Vec2(0.0, 1.0)) == 0.0


class TestSutherlandHodgmanAndCollision:
    def _square(self, cs, cx, cy, half):
        (p,) = cs.create_variables(1)
        assert isinstance(p, Polygon)
        p.set_domain(
            Vec2(cx - half, cy - half),
            Vec2(cx + half, cy - half),
            Vec2(cx + half, cy + half),
            Vec2(cx - half, cy + half),
        )
        return p

    def test_nested_squares_are_inside(self):
        # p1 = [2,2]-[8,8], p2 = [1,1]-[9,9] (TestGeometricConstraintSolver2 fixture).
        cs = RCC2ConstraintSolver()
        p1 = self._square(cs, 5, 5, 3)
        p2 = self._square(cs, 5, 5, 4)
        assert GeometricConstraintSolver._check_inside(p1, p2)
        assert not GeometricConstraintSolver._check_inside(p2, p1)

    def test_disjoint_squares_not_collided(self):
        cs = RCC2ConstraintSolver()
        p1 = self._square(cs, 0, 0, 1)
        p2 = self._square(cs, 100, 100, 1)
        assert not Manifold(p1, p2).is_collided()

    def test_overlapping_squares_collided(self):
        cs = RCC2ConstraintSolver()
        p1 = self._square(cs, 0, 0, 5)
        p2 = self._square(cs, 3, 0, 5)
        assert Manifold(p1, p2).is_collided()

    def test_clip_result_is_intersection_square(self):
        cs = RCC2ConstraintSolver()
        p1 = self._square(cs, 0, 0, 4)  # [-4,-4] to [4,4]
        p2 = self._square(cs, 2, 0, 4)  # [-2,-4] to [6,4]
        slh = SutherlandHodgman(p1, p2)
        clipped = slh.get_clipped_result()
        xs = sorted(v.x for v in clipped)
        ys = sorted(v.y for v in clipped)
        assert abs(xs[0] - (-2.0)) < 1e-6
        assert abs(xs[-1] - 4.0) < 1e-6
        assert abs(ys[0] - (-4.0)) < 1e-6
        assert abs(ys[-1] - 4.0) < 1e-6


class TestGeometricConstraintSolverScenario:
    """Reproduces examples/TestGeometricConstraintSolver.java."""

    def test_scenario(self):
        solver = GeometricConstraintSolver()
        vars_ = solver.create_variables(3, "P")

        p0 = vars_[0]
        assert isinstance(p0, Polygon)
        p0.set_domain(Vec2(1, 1), Vec2(19, 1), Vec2(19, 19), Vec2(1, 19))
        p0.set_movable(True)

        p1 = vars_[1]
        assert isinstance(p1, Polygon)
        p1.set_domain(Vec2(180, 90), Vec2(100, 350), Vec2(340, 350), Vec2(290, 125))
        p1.set_movable(False)

        p2 = vars_[2]
        assert isinstance(p2, Polygon)
        p2.set_domain(Vec2(180, 190), Vec2(100, 50), Vec2(240, 138), Vec2(190, 225))
        p2.set_movable(True)

        inside = GeometricConstraint(Type.INSIDE)
        inside.from_ = p0
        inside.to = p1
        assert solver.add_constraint(inside) is True

        dc1 = GeometricConstraint(Type.DC)
        dc1.from_ = p2
        dc1.to = p1
        assert solver.add_constraint(dc1) is True

        inside1 = GeometricConstraint(Type.INSIDE)
        inside1.from_ = p2
        inside1.to = p0
        assert solver.add_constraint(inside1) is False

        dc = GeometricConstraint(Type.DC)
        dc.from_ = p0
        dc.to = p1
        assert solver.add_constraint(dc) is False


class TestGeometricConstraintSolver2Scenario:
    """Reproduces examples/TestGeometricConstraintSolver2.java."""

    def test_scenario(self):
        solver = GeometricConstraintSolver()
        vars_ = solver.create_variables(2, "pol")

        p1 = vars_[0]
        assert isinstance(p1, Polygon)
        p1.set_domain(Vec2(2, 2), Vec2(8, 2), Vec2(8, 8), Vec2(2, 8))
        p1.set_movable(False)

        p2 = vars_[1]
        assert isinstance(p2, Polygon)
        p2.set_domain(Vec2(1, 1), Vec2(9, 1), Vec2(9, 9), Vec2(1, 9))
        p2.set_movable(False)

        inside = GeometricConstraint(Type.INSIDE)
        inside.from_ = vars_[0]
        inside.to = vars_[1]
        assert solver.add_constraint(inside) is True


class TestRCC2ConstraintSolverScenario:
    """Reproduces examples/TestRCC2ConstraintSolver.java."""

    def test_scenario(self):
        solver = RCC2ConstraintSolver()
        vars_ = solver.create_variables(3)

        p0 = vars_[0]
        assert isinstance(p0, Polygon)
        p0.set_domain(Vec2(100, 87), Vec2(60, 30), Vec2(220, 60), Vec2(180, 120))
        p0.set_movable(True)

        p1 = vars_[1]
        assert isinstance(p1, Polygon)
        p1.set_domain(Vec2(180, 90), Vec2(100, 350), Vec2(340, 350), Vec2(290, 125))
        p1.set_movable(False)

        p2 = vars_[2]
        assert isinstance(p2, Polygon)
        p2.set_domain(Vec2(180, 190), Vec2(100, 50), Vec2(240, 138), Vec2(190, 225))
        p2.set_movable(True)

        inside = GeometricConstraint(Type.INSIDE)
        inside.from_ = p0
        inside.to = p1
        assert solver.add_constraint(inside) is True

        dc1 = GeometricConstraint(Type.DC)
        dc1.from_ = p2
        dc1.to = p1
        assert solver.add_constraint(dc1) is True

        inside1 = GeometricConstraint(Type.INSIDE)
        inside1.from_ = p2
        inside1.to = p0
        assert solver.add_constraint(inside1) is False
