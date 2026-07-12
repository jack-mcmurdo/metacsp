"""Port of examples/TestBooleanSatisfiabilitySolverSATAlternative2.java."""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


def main() -> None:
    solver = BooleanSatisfiabilitySolver(10, 10)

    # (~x1 v x2 v x4) ^ (x1 v ~x2 v x3) ^ (x1 v x2 v ~x4) ^ (x2 v x3) ^
    # (x1 v x2 v ~x3 v x4) ^ (x1 v ~x2 v ~x3 v x4) ^ (x1 v ~x2 v ~x3 v ~x4) ^
    # (~x1 v ~x2 v ~x3 v x4) ^ (~x1 v x2 v ~x3 v ~x4) ^ (~x1 v ~x2 v ~x3 v ~x4)
    vars_ = solver.create_variables(4)
    cnf = (
        "((((((((((~x1 v (x2 v x4)) ^ (x1 v (~x2 v x3))) ^ (x1 v (x2 v ~x4))) ^ (x2 v x3)) ^ "
        "(x1 v (x2 v (~x3 v x4)))) ^ (x1 v (~x2 v (~x3 v x4)))) ^ (x1 v (~x2 v (~x3 v ~x4)))) ^ "
        "(~x1 v (~x2 v (~x3 v x4)))) ^ (~x1 v (x2 v (~x3 v ~x4)))) ^ (~x1 v (~x2 v (~x3 v ~x4))))"
    )
    cons = BooleanConstraint.create_boolean_constraints(vars_, cnf)
    print("SAT?", solver.add_constraints(*cons))
    print(vars_)


if __name__ == "__main__":
    main()
