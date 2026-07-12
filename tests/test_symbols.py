"""Tests for metacsp.multi.symbols (M7), derived from the assertable behavior
of examples/multi/TestSymbolicVariableConstraintSolver{,Simple,NoReasoing}.java
(there is no dedicated JUnit test for the non-fuzzy symbolic solver)."""

from __future__ import annotations

import pytest

from metacsp.exceptions import NoSymbolsException
from metacsp.multi.symbols import (
    SymbolicValueConstraint,
    SymbolicVariable,
    SymbolicVariableConstraintSolver,
)

Type = SymbolicValueConstraint.Type


class TestSymbolicVariableConstraintSolver:
    def test_different_and_value_constraints(self):
        symbols = ["A", "B", "C", "D", "E", "F", "G"]
        solver = SymbolicVariableConstraintSolver(symbols, 100)
        v0, v1 = solver.create_variables(2)
        assert isinstance(v0, SymbolicVariable) and isinstance(v1, SymbolicVariable)
        v0.set_symbolic_domain("B", "D", "F", "S1", "S2")

        con1 = SymbolicValueConstraint(Type.DIFFERENT)
        con1.set_from(v0)
        con1.set_to(v1)
        assert solver.add_constraint(con1) is True

        con3 = SymbolicValueConstraint(Type.VALUEDIFFERENT)
        con3.value = ["B", "F"]
        con3.set_from(v1)
        con3.set_to(v1)
        assert solver.add_constraint(con3) is True
        assert "B" not in v1.symbols
        assert "F" not in v1.symbols

    def test_equals_constraint_propagates_domain(self):
        symbols = ["A", "B", "C", "D", "E", "F", "G"]
        solver = SymbolicVariableConstraintSolver(symbols, 100)
        v0, v1, v2 = solver.create_variables(3)
        assert isinstance(v0, SymbolicVariable)
        v0.set_symbolic_domain("B", "D", "F")

        con1 = SymbolicValueConstraint(Type.EQUALS)
        con1.set_from(v0)
        con1.set_to(v1)
        assert solver.add_constraint(con1) is True
        assert set(v1.symbols) == {"B", "D", "F"}

        solver.remove_variable(v2)
        assert v2 not in solver.get_variables()

        solver.remove_constraint(con1)
        assert con1 not in solver.get_constraints()

    def test_equals_constraint_without_vocabulary_raises(self):
        """A SymbolicVariableConstraintSolver created with no vocabulary
        (the "no reasoning" solver) cannot support inter-variable EQUALS
        constraints -- only per-variable non-solver-domain symbols."""
        solver = SymbolicVariableConstraintSolver()
        v0, v1 = solver.create_variables(2)
        assert isinstance(v0, SymbolicVariable) and isinstance(v1, SymbolicVariable)
        v0.set_symbolic_domain("A", "B", "C", "D")
        v1.set_symbolic_domain("alpha", "beta", "gamma", "delta")

        con = SymbolicValueConstraint(Type.EQUALS)
        con.set_from(v0)
        con.set_to(v1)

        with pytest.raises(NoSymbolsException):
            solver.add_constraint(con)
