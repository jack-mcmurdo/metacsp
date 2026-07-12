"""Port of examples/TestBooleanSatisfiabilitySolverSATAlternative1.java."""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


def main() -> None:
    solver = BooleanSatisfiabilitySolver(10, 10)

    # (~x1 v x2 v x4) ^ (x1 v ~x2 v x3) ^ (x1 v x2 v ~x4) ^ (x2 v x3) ^
    # (x1 v x2 v ~x3 v x4) ^ (x1 v ~x2 v ~x3 v x4) ^ (x1 v ~x2 v ~x3 v ~x4) ^
    # (~x1 v ~x2 v ~x3 v x4) ^ (~x1 v x2 v ~x3 v ~x4) ^ (~x1 v ~x2 v ~x3 v ~x4)
    vars_ = solver.create_variables(4)
    clause1 = BooleanConstraint([vars_[0], vars_[1], vars_[3]], [False, True, True])
    clause2 = BooleanConstraint([vars_[0], vars_[1], vars_[2]], [True, False, True])
    clause3 = BooleanConstraint([vars_[0], vars_[1], vars_[3]], [True, True, False])
    clause4 = BooleanConstraint([vars_[1], vars_[2]], [True, True])

    clause5 = BooleanConstraint([vars_[0], vars_[1], vars_[2], vars_[3]], [True, True, False, True])
    clause6 = BooleanConstraint(
        [vars_[0], vars_[1], vars_[2], vars_[3]], [True, False, False, True]
    )
    clause7 = BooleanConstraint(
        [vars_[0], vars_[1], vars_[2], vars_[3]], [True, False, False, False]
    )

    clause8 = BooleanConstraint(
        [vars_[0], vars_[1], vars_[2], vars_[3]], [False, False, False, True]
    )
    clause9 = BooleanConstraint(
        [vars_[0], vars_[1], vars_[2], vars_[3]], [False, True, False, False]
    )
    clause10 = BooleanConstraint(
        [vars_[0], vars_[1], vars_[2], vars_[3]], [False, False, False, False]
    )

    print(
        "SAT?",
        solver.add_constraints(
            clause1,
            clause2,
            clause3,
            clause4,
            clause5,
            clause6,
            clause7,
            clause8,
            clause9,
            clause10,
        ),
    )
    print(vars_)
    print("Chosen value for", vars_[1], "is", vars_[1].domain.choose_value("model1"))


if __name__ == "__main__":
    main()
