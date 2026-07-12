"""Port of examples/TestBooleanSatisfiabilitySolverSATNonCNF.java."""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


def main() -> None:
    solver = BooleanSatisfiabilitySolver(10, 10)
    vars_ = solver.create_variables(4)
    wff = "((x1 <-> ((x2 v ~x3) ^ ~(x2 v ~x3))) ^ (x4 v ~x4))"
    cons = BooleanConstraint.create_boolean_constraints(vars_, wff)

    print("SAT?", solver.add_constraints(*cons))
    print(vars_)


if __name__ == "__main__":
    main()
