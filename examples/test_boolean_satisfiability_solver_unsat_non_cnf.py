"""Port of examples/TestBooleanSatisfiabilitySolverUNSATNonCNF.java."""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


def main() -> None:
    solver = BooleanSatisfiabilitySolver(10, 10)
    vars_ = solver.create_variables(3)
    wff = "((x1 <-> ((x2 v ~x3) ^ ~(x2 v ~x3))) ^ (x1))"
    cons = BooleanConstraint.create_boolean_constraints(vars_, wff)

    print("SAT?", solver.add_constraints(*cons))
    print(vars_)


if __name__ == "__main__":
    main()
