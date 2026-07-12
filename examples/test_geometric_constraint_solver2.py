"""Port of examples/TestGeometricConstraintSolver2.java.

The Java original draws the resulting network (Swing PolygonFrame, not
ported -- see D10) and sleeps for animation purposes; both are dropped here.
"""

from __future__ import annotations

from metacsp.spatial.geometry import GeometricConstraint, GeometricConstraintSolver, Polygon, Vec2

Type = GeometricConstraint.Type


def main() -> None:
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
    print("Added?", solver.add_constraint(inside))


if __name__ == "__main__":
    main()
