"""Port of tests/TestAPSPSolver.java."""

from __future__ import annotations

from metacsp.time import APSPSolver, SimpleDistanceConstraint


class TestAPSPSolver:
    def test_bounds_after_propagation(self):
        solver = APSPSolver(100, 500)
        one, two, three = solver.create_variables(3)

        con1 = SimpleDistanceConstraint()
        con1.from_ = solver.get_variable(0)
        con1.to = one
        con1.minimum = 60
        con1.maximum = 75

        con2 = SimpleDistanceConstraint()
        con2.from_ = one
        con2.to = two
        con2.minimum = 7
        con2.maximum = 9

        con3 = SimpleDistanceConstraint()
        con3.from_ = solver.get_variable(0)
        con3.to = two
        con3.minimum = 68
        con3.maximum = 70

        assert solver.add_constraints(con1, con2, con3) is True

        con4 = SimpleDistanceConstraint()
        con4.from_ = two
        con4.to = three
        con4.minimum = 56
        con4.maximum = 100

        assert solver.add_constraint(con4) is True

        con5 = SimpleDistanceConstraint()
        con5.from_ = one
        con5.to = three
        con5.minimum = 70
        con5.maximum = 100

        assert solver.add_constraint(con5) is True

        assert one.domain.choose_value("ET") == 160
        assert one.domain.choose_value("LT") == 163
        assert two.domain.choose_value("ET") == 168
        assert two.domain.choose_value("LT") == 170
        assert three.domain.choose_value("ET") == 230
        assert three.domain.choose_value("LT") == 263

    def test_inconsistency(self):
        solver = APSPSolver(100, 500)
        one, two, three = solver.create_variables(3)

        con1 = SimpleDistanceConstraint()
        con1.from_ = one
        con1.to = two
        con1.minimum = 5
        con1.maximum = 100

        con2 = SimpleDistanceConstraint()
        con2.from_ = two
        con2.to = three
        con2.minimum = 5
        con2.maximum = 100

        assert solver.add_constraints(con1, con2) is True

        con3 = SimpleDistanceConstraint()
        con3.from_ = three
        con3.to = one
        con3.minimum = 5
        con3.maximum = 100

        assert solver.add_constraints(con3) is False

        con4 = SimpleDistanceConstraint()
        con4.from_ = one
        con4.to = three
        con4.minimum = 5
        con4.maximum = 100

        assert solver.add_constraints(con4) is True
