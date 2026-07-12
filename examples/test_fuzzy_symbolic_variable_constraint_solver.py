"""Port of examples/TestFuzzySymbolicVariableConstraintSolver.java.

The Java original loops forever, alternately adding and removing con1/con2
and printing the resulting value possibility. Here the loop runs once (one
add pass, one remove pass) so the script exits cleanly; the expected printed
sequence (per the Java source's own comment) is 0.2, 0.1, 0.5, 1.0.
"""

from __future__ import annotations

from metacsp.fuzzy_symbols import FuzzySymbolicVariableConstraintSolver
from metacsp.multi.symbols import SymbolicValueConstraint


def main() -> None:
    solver = FuzzySymbolicVariableConstraintSolver()
    var0, var1, var2 = solver.create_variables(3)

    var0.set_domain(["A", "B", "C"], [0.1, 0.8, 1.0])
    var1.set_domain(["A", "B", "C"], [0.5, 0.1, 0.2])
    var2.set_domain(["A", "B", "C"], [0.9, 0.3, 0.1])

    con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
    con1.set_from(var0)
    con1.set_to(var1)

    con2 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
    con2.set_from(var1)
    con2.set_to(var2)

    cons = [con1, con2]

    for con in cons:
        solver.add_constraint(con)
        print("Value Possibility:", solver.get_upper_bound())
    for con in cons:
        solver.remove_constraint(con)
        print("Value Possibility:", solver.get_upper_bound())


if __name__ == "__main__":
    main()
