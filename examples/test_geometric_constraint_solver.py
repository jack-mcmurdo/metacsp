"""Port of examples/TestGeometricConstraintSolver.java.

The Java original draws the resulting network (Swing PolygonFrame, not
ported -- see D10) and sleeps between steps for animation purposes; both
are dropped here.
"""

from __future__ import annotations

from metacsp.spatial.geometry import GeometricConstraint, GeometricConstraintSolver, Polygon, Vec2

Type = GeometricConstraint.Type


def main() -> None:
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
    print("Added?", solver.add_constraint(inside))

    dc1 = GeometricConstraint(Type.DC)
    dc1.from_ = p2
    dc1.to = p1
    print("Added?", solver.add_constraint(dc1))

    inside1 = GeometricConstraint(Type.INSIDE)
    inside1.from_ = p2
    inside1.to = p0
    print("Added?", solver.add_constraint(inside1))

    dc = GeometricConstraint(Type.DC)
    dc.from_ = p0
    dc.to = p1
    print("Added?", solver.add_constraint(dc))


if __name__ == "__main__":
    main()
