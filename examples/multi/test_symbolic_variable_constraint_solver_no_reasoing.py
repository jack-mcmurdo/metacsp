"""Port of examples/multi/TestSymbolicVariableConstraintSolverNoReasoing.java (sic)."""

from __future__ import annotations

from metacsp.exceptions import NoSymbolsException
from metacsp.multi.symbols import (
    SymbolicValueConstraint,
    SymbolicVariable,
    SymbolicVariableConstraintSolver,
)

Type = SymbolicValueConstraint.Type


def main() -> None:
    solver = SymbolicVariableConstraintSolver()
    vars_ = solver.create_variables(2)

    var0 = vars_[0]
    var1 = vars_[1]
    assert isinstance(var0, SymbolicVariable) and isinstance(var1, SymbolicVariable)
    var0.set_symbolic_domain("A", "B", "C", "D")
    var1.set_symbolic_domain("alpha", "beta", "gamma", "delta")

    con = SymbolicValueConstraint(Type.EQUALS)
    con.set_from(vars_[0])
    con.set_to(vars_[1])

    try:
        solver.add_constraint(con)
    except NoSymbolsException as e:
        print(e)


if __name__ == "__main__":
    main()
