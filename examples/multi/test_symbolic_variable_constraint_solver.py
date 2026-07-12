"""Port of examples/multi/TestSymbolicVariableConstraintSolver.java."""

from __future__ import annotations

from metacsp.multi.symbols import (
    SymbolicValueConstraint,
    SymbolicVariable,
    SymbolicVariableConstraintSolver,
)

Type = SymbolicValueConstraint.Type


def main() -> None:
    symbols = ["A", "B", "C", "D", "E", "F", "G"]
    solver = SymbolicVariableConstraintSolver(symbols, 100)
    vars_ = solver.create_variables(2)

    cast_var0 = vars_[0]
    assert isinstance(cast_var0, SymbolicVariable)
    cast_var0.set_symbolic_domain("B", "D", "F", "S1", "S2")

    con1 = SymbolicValueConstraint(Type.DIFFERENT)
    con1.set_from(vars_[0])
    con1.set_to(vars_[1])

    con2 = SymbolicValueConstraint(Type.VALUEEQUALS)
    con2.value = ["B", "D", "F", "G"]
    con2.set_from(vars_[0])
    con2.set_to(vars_[0])

    con3 = SymbolicValueConstraint(Type.VALUEDIFFERENT)
    con3.value = ["B", "F"]
    con3.set_from(vars_[1])
    con3.set_to(vars_[1])

    print("Added con1?", solver.add_constraint(con1))
    print("Added con2?", solver.add_constraint(con2))
    print("Added con3?", solver.add_constraint(con3))


if __name__ == "__main__":
    main()
