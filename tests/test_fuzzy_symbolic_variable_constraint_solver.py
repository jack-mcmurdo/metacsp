"""Port of tests/TestFuzzySymbolicVariableConstraintSolver.java."""

from __future__ import annotations

from metacsp.fuzzy_symbols import FuzzySymbolicVariableConstraintSolver
from metacsp.multi.symbols import SymbolicValueConstraint


class TestFuzzySymbolicVariableConstraintSolver:
    def test_value_possibility(self):
        solver = FuzzySymbolicVariableConstraintSolver()
        var0, var1, var2 = solver.create_variables(3)

        var0.set_domain(["A", "B", "C"], [0.1, 0.8, 1.0])
        var1.set_domain(["A", "B", "C"], [0.5, 0.1, 0.2])
        var2.set_domain(["A", "B", "C"], [0.9, 0.3, 0.1])

        assert solver.get_upper_bound() == 1.0

        con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
        con1.set_from(var0)
        con1.set_to(var1)
        assert solver.add_constraint(con1) is True
        assert solver.get_upper_bound() == 0.2

        con2 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
        con2.set_from(var1)
        con2.set_to(var2)
        assert solver.add_constraint(con2) is True
        assert solver.get_upper_bound() == 0.1

        solver.remove_constraint(con1)
        assert solver.get_upper_bound() == 0.5

        solver.remove_constraint(con2)
        assert solver.get_upper_bound() == 1.0
