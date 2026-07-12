"""Port of tests/TestRCCConstraintNetworkSolver.java."""

from __future__ import annotations

from metacsp.spatial.rcc import RCCConstraint, RCCConstraintSolver, Region

Type = RCCConstraint.Type


def test_consistency() -> None:
    solver = RCCConstraintSolver()
    vars_ = solver.create_variables(3)
    assert vars_ is not None

    re0 = vars_[0]
    re1 = vars_[1]
    re2 = vars_[2]
    assert isinstance(re0, Region)
    assert isinstance(re1, Region)
    assert isinstance(re2, Region)

    con0 = RCCConstraint(Type.NTPP, Type.PO)
    con0.from_ = re0
    con0.to = re1
    assert solver.add_constraint(con0)

    con1 = RCCConstraint(Type.DC)
    con1.from_ = re1
    con1.to = re2
    assert solver.add_constraint(con1)


def test_inconsistency() -> None:
    solver = RCCConstraintSolver()
    vars_ = solver.create_variables(3)
    assert vars_ is not None

    re0 = vars_[0]
    re1 = vars_[1]
    re2 = vars_[2]
    assert isinstance(re0, Region)
    assert isinstance(re1, Region)
    assert isinstance(re2, Region)

    con0 = RCCConstraint(Type.NTPP, Type.PO)
    con0.from_ = re0
    con0.to = re1

    con1 = RCCConstraint(Type.DC)
    con1.from_ = re1
    con1.to = re2

    con2 = RCCConstraint(Type.NTPPI)
    con2.from_ = re2
    con2.to = re0

    assert not solver.add_constraints(con0, con1, con2)
