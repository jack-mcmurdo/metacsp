"""Port of examples/TestDE9IMRelationSolverSimple.java.

The Java original ends with ``ConstraintNetwork.draw(...)`` (Swing, not
ported -- see D10); dropped here.
"""

from __future__ import annotations

from metacsp.multi.spatial.de9im import DE9IMRelation, DE9IMRelationSolver


def main() -> None:
    solver = DE9IMRelationSolver()
    vars_ = solver.create_variables(3)
    assert vars_ is not None

    relation1 = DE9IMRelation(DE9IMRelation.Type.Contains)
    relation1.from_ = vars_[0]
    relation1.to = vars_[1]

    relation2 = DE9IMRelation(DE9IMRelation.Type.Contains)
    relation2.from_ = vars_[1]
    relation2.to = vars_[2]

    relation3 = DE9IMRelation(DE9IMRelation.Type.Contains)
    relation3.from_ = vars_[2]
    relation3.to = vars_[0]

    print(solver.add_constraints(relation1))


if __name__ == "__main__":
    main()
