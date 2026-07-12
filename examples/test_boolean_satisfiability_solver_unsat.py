"""Port of examples/TestBooleanSatisfiabilitySolverUNSAT.java.

The Java original sleeps between steps to allow a Swing viewer (not ported,
see D10) to visualize the incremental network changes.
"""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


def main() -> None:
    solver = BooleanSatisfiabilitySolver(10, 10)

    # (~x1 v x2) ^ (x1 v x2) ^ (x1 v ~x2) ^ (~x1 v ~x2)
    vars_ = solver.create_variables(2)
    clause1 = BooleanConstraint([vars_[0], vars_[1]], [False, True])
    clause2 = BooleanConstraint([vars_[0], vars_[1]], [True, True])
    clause3 = BooleanConstraint([vars_[0], vars_[1]], [True, False])
    clause4 = BooleanConstraint([vars_[0], vars_[1]], [False, False])

    # This will succeed
    print("SAT?", solver.add_constraints(clause1, clause2, clause3))
    print(solver.get_variables())

    # This will fail
    print("SAT?", solver.add_constraint(clause4))
    print(solver.get_variables())

    solver.remove_constraint(clause3)
    print(solver.get_variables())

    # (~x1 v x3) ^ (x2 v ~x3)
    new_vars = solver.create_variables(1)
    clause5 = BooleanConstraint([vars_[0], new_vars[0]], [False, False])
    clause6 = BooleanConstraint([vars_[1], new_vars[0]], [True, False])

    # This will succeed
    print("SAT?", solver.add_constraints(clause5, clause6))
    print(solver.get_variables())

    solver.remove_constraints([clause5, clause6])
    print(solver.get_variables())

    solver.remove_variable(new_vars[0])
    print(solver.get_variables())

    print("Chosen value for", vars_[0], "is", vars_[0].domain.choose_value("model1"))


if __name__ == "__main__":
    main()
