"""Port of examples/TestDE9IMRelationSolver.java.

The Java original ends with ``ConstraintNetwork.draw(...)`` and a
``JTSDrawingPanel`` (Swing, not ported -- see D10); dropped here.
"""

from __future__ import annotations

from metacsp.multi.spatial.de9im import (
    DE9IMRelation,
    DE9IMRelationSolver,
    GeometricShapeVariable,
    LineStringDomain,
    PointDomain,
    PolygonalDomain,
)


def main() -> None:
    solver = DE9IMRelationSolver()
    vars_ = solver.create_variables(4)
    assert vars_ is not None

    coord1 = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    g1 = vars_[0]
    assert isinstance(g1, GeometricShapeVariable)
    g1.domain = PolygonalDomain(g1, coord1)

    coord2 = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    g2 = vars_[1]
    assert isinstance(g2, GeometricShapeVariable)
    g2.domain = PolygonalDomain(g2, coord2)

    coord3 = [(-40.0, -40.0), (0.0, 0.0), (10.0, 5.0), (11.0, 200.0)]
    g3 = vars_[2]
    assert isinstance(g3, GeometricShapeVariable)
    g3.domain = LineStringDomain(g3, coord3)

    g4 = vars_[3]
    assert isinstance(g4, GeometricShapeVariable)
    g4.domain = PointDomain(g4, (-2.0, -2.0))

    implicit_relations = solver.get_all_implicit_relations()
    print(f"All implicit relations:\n{implicit_relations}")

    rcc8_implicit_relations = solver.get_all_implicit_rcc8_relations()
    print(f"All implicit RCC8 relations:\n{rcc8_implicit_relations}")

    relation = DE9IMRelation(DE9IMRelation.Type.Disjoint)
    relation.from_ = g1
    relation.to = g2
    print(solver.add_constraints(relation))

    for var in vars_:
        assert isinstance(var, GeometricShapeVariable)
        print(f"{var}: {var.shape_type}")


if __name__ == "__main__":
    main()
