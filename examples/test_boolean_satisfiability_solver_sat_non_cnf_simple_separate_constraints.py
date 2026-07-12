"""Port of examples/TestBooleanSatisfiabilitySolverSATNonCNFSimpleSeparateConstraints.java."""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


def main() -> None:
    solver = BooleanSatisfiabilitySolver(10, 10)
    vars_ = solver.create_variables(4)

    # Equivalent to "((((x1 ^ x2) ^ (x2 v (~x3 ^ x4))) ^ (~x1 v x3)) ^ (x2 v (~x3 ^ ~x4)))"
    # split into three separately-added constraint sets.
    wff = "((x1 ^ x2) ^ (~x1 v x3))"
    cons = BooleanConstraint.create_boolean_constraints([vars_[0], vars_[1], vars_[2]], wff)
    print("SAT?", solver.add_constraints(*cons))

    wff = "(x1 v (~x2 ^ x3))"
    cons1 = BooleanConstraint.create_boolean_constraints([vars_[1], vars_[2], vars_[3]], wff)
    print("SAT?", solver.add_constraints(*cons1))

    wff = "(x1 v (~x2 ^ ~x3))"
    cons2 = BooleanConstraint.create_boolean_constraints([vars_[1], vars_[2], vars_[3]], wff)
    print("SAT?", solver.add_constraints(*cons2))

    print(vars_)


if __name__ == "__main__":
    main()
