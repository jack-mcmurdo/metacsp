"""Port of examples/multi/TestFuzzyActivityNetworkSolver.java.

The Java original loops forever, alternately removing and re-adding con1/con2.
Here the loop runs a few bounded iterations so the script exits cleanly.
"""

from __future__ import annotations

from metacsp.fuzzy_allen_interval import FuzzyAllenIntervalConstraint
from metacsp.multi.fuzzy_activity import FuzzyActivityNetworkSolver
from metacsp.multi.symbols import SymbolicValueConstraint


def main() -> None:
    solver = FuzzyActivityNetworkSolver()

    act1 = solver.create_variable()
    act1.set_domain(["A", "B", "C"], [0.1, 0.4, 0.8])

    act2 = solver.create_variable()
    act2.set_domain(["A", "B", "C"], [0.8, 0.2, 0.7])

    con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
    con1.set_from(act1)
    con1.set_to(act2)

    con2 = FuzzyAllenIntervalConstraint(FuzzyAllenIntervalConstraint.Type.Before)
    con2.from_ = act1
    con2.to = act2

    cons = [con1, con2]
    solver.add_constraints(*cons)

    print(solver.description)
    print(act1.description)

    print("---------------------------------")
    print("Temporal Possibility:", solver.get_temporal_consistency())
    print("Value Possibility:", solver.get_value_consistency())
    print("---------------------------------")

    add = False
    for _ in range(2):
        for con in cons:
            if add:
                solver.add_constraint(con)
                print("Added", type(con).__name__, "type")
            else:
                solver.remove_constraint(con)
                print("Removed", type(con).__name__, "type")
            print("Temporal Possibility:", solver.get_temporal_consistency())
            print("Value Possibility:", solver.get_value_consistency())
            print("---------------------------------")
        add = not add


if __name__ == "__main__":
    main()
