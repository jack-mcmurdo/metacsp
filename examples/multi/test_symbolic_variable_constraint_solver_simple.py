"""Port of examples/multi/TestSymbolicVariableConstraintSolverSimple.java."""

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
    vars_ = solver.create_variables(3)

    print("Created variables", vars_)

    var0 = vars_[0]
    assert isinstance(var0, SymbolicVariable)
    var0.set_symbolic_domain("B", "D", "F")

    con1 = SymbolicValueConstraint(Type.EQUALS)
    con1.set_from(vars_[0])
    con1.set_to(vars_[1])
    print("Added con1?", solver.add_constraint(con1))

    print("Removing variable", vars_[2])
    solver.remove_variable(vars_[2])
    print("Done!")

    print("Removing constraint", con1)
    solver.remove_constraint(con1)
    print("Done!")


if __name__ == "__main__":
    main()
