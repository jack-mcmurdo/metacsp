"""Port of examples/multi/TestFuzzySetActivityNetworkSolver.java."""

from __future__ import annotations

from metacsp.multi.fuzzy_set_activity import FuzzySetActivityNetworkSolver
from metacsp.multi.symbols import SymbolicValueConstraint


def main() -> None:
    solver = FuzzySetActivityNetworkSolver(0, 10000)

    act1 = solver.create_variable()
    act1.set_domain(["A"], [1.0])

    act2 = solver.create_variable()
    act2.set_domain(["A"], [1.0])

    con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.DIFFERENT)
    con1.set_from(act1)
    con1.set_to(act2)

    solver.add_constraints(con1)

    print("---------------------------------")
    print("Value Possibility:", solver.get_value_consistency())
    print("---------------------------------")


if __name__ == "__main__":
    main()
