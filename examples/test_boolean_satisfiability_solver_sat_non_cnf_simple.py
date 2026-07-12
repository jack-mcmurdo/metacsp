"""Port of examples/TestBooleanSatisfiabilitySolverSATNonCNFSimple.java."""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


def main() -> None:
    solver = BooleanSatisfiabilitySolver(10, 10)
    vars_ = solver.create_variables(4)
    # NOTE: All parentheses need to be explicit (every binary connective must be parenthesized)
    # ... therefore the following is not OK:
    # wff = "(x1 ^ x2) ^ (x2 v ~x3 ^ x4) ^ (~x1 v x3) ^ (x2 v ~x3 ^ ~x4)"
    # ... but the following is OK:
    # wff = "((((x1 ^ x2) ^ (x2 v (~x3 ^ x4))) ^ (~x1 v x3)) ^ (x2 v (~x3 ^ ~x4)))"
    # ... as well as the following:
    wff = "(((x1 ^ x2) ^ (x2 v (~x3 ^ x4))) ^ ((~x1 v x3) ^ (x2 v (~x3 ^ ~x4))))"
    cons = BooleanConstraint.create_boolean_constraints(vars_, wff)

    print("SAT?", solver.add_constraints(*cons))
    print(vars_)


if __name__ == "__main__":
    main()
