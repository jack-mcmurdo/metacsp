"""Port of tests/TestFuzzyAllenIntervalNetworkSolver.java."""

from __future__ import annotations

from metacsp.fuzzy_allen_interval import (
    FuzzyAllenIntervalConstraint,
    FuzzyAllenIntervalNetworkSolver,
)

Type = FuzzyAllenIntervalConstraint.Type


class TestFuzzyAllenIntervalNetworkSolver:
    def test_possibility_degree(self):
        solver = FuzzyAllenIntervalNetworkSolver()
        act0, act1, act2 = solver.create_variables(3)

        con0 = FuzzyAllenIntervalConstraint(Type.After)
        con0.from_ = act0
        con0.to = act1

        con1 = FuzzyAllenIntervalConstraint(Type.Contains)
        con1.from_ = act1
        con1.to = act2

        con3 = FuzzyAllenIntervalConstraint(Type.Meets)
        con3.from_ = act2
        con3.to = act0

        assert solver.add_constraints(con0, con1, con3) is True
        assert solver.get_posibility_degree() == 0.8
