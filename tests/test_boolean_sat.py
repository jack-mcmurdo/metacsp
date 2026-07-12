"""Port of tests/TestBooleanSAT.java."""

from __future__ import annotations

from metacsp.boolean_sat import BooleanConstraint, BooleanSatisfiabilitySolver


class TestBooleanSAT:
    def test_boolean_sat_result(self):
        solver = BooleanSatisfiabilitySolver(10, 10)

        # (~x1 v x2 v x4) ^ (x1 v ~x2 v x3) ^ (x1 v x2 v ~x4) ^ (x2 v x3) ^
        # (x1 v x2 v ~x3 v x4) ^ (x1 v ~x2 v ~x3 v x4) ^ (x1 v ~x2 v ~x3 v ~x4) ^
        # (~x1 v ~x2 v ~x3 v x4) ^ (~x1 v x2 v ~x3 v ~x4) ^ (~x1 v ~x2 v ~x3 v ~x4)
        vars_ = solver.create_variables(4)
        clause1 = BooleanConstraint([vars_[0], vars_[1], vars_[3]], [False, True, True])
        clause2 = BooleanConstraint([vars_[0], vars_[1], vars_[2]], [True, False, True])
        clause3 = BooleanConstraint([vars_[0], vars_[1], vars_[3]], [True, True, False])
        clause4 = BooleanConstraint([vars_[1], vars_[2]], [True, True])

        clause5 = BooleanConstraint(
            [vars_[0], vars_[1], vars_[2], vars_[3]], [True, True, False, True]
        )
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

        assert (
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
            )
            is True
        )
        assert vars_[0].domain.can_be_true and not vars_[0].domain.can_be_false
        assert vars_[1].domain.can_be_true and not vars_[1].domain.can_be_false
        assert not vars_[2].domain.can_be_true and vars_[2].domain.can_be_false
        assert vars_[3].domain.can_be_true and vars_[3].domain.can_be_false

    def test_boolean_sat_result_with_wff(self):
        solver = BooleanSatisfiabilitySolver(10, 10)
        vars_ = solver.create_variables(4)
        wff = "((x1 <-> ((x2 v ~x3) ^ ~(x2 v ~x3))) ^ (x4 v ~x4))"
        cons = BooleanConstraint.create_boolean_constraints(vars_, wff)

        assert solver.add_constraints(*cons) is True
        assert not vars_[0].domain.can_be_true and vars_[0].domain.can_be_false
        assert vars_[1].domain.can_be_true and not vars_[1].domain.can_be_false
        assert not vars_[2].domain.can_be_true and vars_[2].domain.can_be_false
        assert vars_[3].domain.can_be_true and vars_[3].domain.can_be_false

    def test_boolean_sat_and_unsat_result(self):
        solver = BooleanSatisfiabilitySolver(10, 10)

        # (~x1 v x2) ^ (x1 v x2) ^ (x1 v ~x2) ^ (~x1 v ~x2)
        vars_ = solver.create_variables(2)
        clause1 = BooleanConstraint([vars_[0], vars_[1]], [False, True])
        clause2 = BooleanConstraint([vars_[0], vars_[1]], [True, True])
        clause3 = BooleanConstraint([vars_[0], vars_[1]], [True, False])
        clause4 = BooleanConstraint([vars_[0], vars_[1]], [False, False])

        # This will succeed
        assert solver.add_constraints(clause1, clause2, clause3) is True
        # This will fail
        assert solver.add_constraint(clause4) is False
        solver.remove_constraint(clause3)
        # (~x1 v x3) ^ (x2 v ~x3)
        new_vars = solver.create_variables(1)
        clause5 = BooleanConstraint([vars_[0], new_vars[0]], [False, False])
        clause6 = BooleanConstraint([vars_[1], new_vars[0]], [True, False])
        # This will succeed
        assert solver.add_constraints(clause5, clause6) is True
        solver.remove_constraints([clause5, clause6])
        solver.remove_variable(new_vars[0])
        assert vars_[0].domain.can_be_true and vars_[0].domain.can_be_false
        assert vars_[1].domain.can_be_true and not vars_[1].domain.can_be_false

    def test_boolean_unsat_result_with_wff(self):
        solver = BooleanSatisfiabilitySolver(10, 10)
        vars_ = solver.create_variables(3)
        wff = "((x1 <-> ((x2 v ~x3) ^ ~(x2 v ~x3))) ^ (x1))"
        cons = BooleanConstraint.create_boolean_constraints(vars_, wff)
        assert solver.add_constraints(*cons) is False
