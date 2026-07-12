"""Port of examples/TestRCCConstraintNetworkSolver.java.

The Java original ends with ``ConstraintNetwork.draw(...)`` (Swing, not
ported -- see D10); dropped here.
"""

from __future__ import annotations

from metacsp.spatial.rcc import RCCConstraint, RCCConstraintSolver, Region

Type = RCCConstraint.Type


def main() -> None:
    solver = RCCConstraintSolver()
    vars_ = solver.create_variables(3)
    assert vars_ is not None

    re0 = vars_[0]
    re1 = vars_[1]
    re2 = vars_[2]
    assert isinstance(re0, Region)
    assert isinstance(re1, Region)
    assert isinstance(re2, Region)

    con0 = RCCConstraint(Type.NTPP, Type.TPP)
    con0.from_ = re0
    con0.to = re1
    print(f"Adding constraint {con0}: {solver.add_constraint(con0)}")

    con1 = RCCConstraint(Type.DC)
    con1.from_ = re1
    con1.to = re2
    print(f"Adding constraint {con1}: {solver.add_constraint(con1)}")

    con3 = RCCConstraint(Type.EC)
    con3.from_ = re0
    con3.to = re2
    print(f"Adding constraint {con3}: {solver.add_constraint(con3)}")


if __name__ == "__main__":
    main()
