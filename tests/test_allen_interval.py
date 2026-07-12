"""Port of tests/multi/TestAllenInterval.java."""

from __future__ import annotations

from metacsp.multi.activity import ActivityNetworkSolver
from metacsp.multi.allen_interval import AllenIntervalConstraint, AllenIntervalNetworkSolver
from metacsp.time import APSPSolver, Bounds

Type = AllenIntervalConstraint.Type


class TestAllenInterval:
    def test_no_default_bounds(self):
        """A bug caused by creating AllenIntervals on AllenIntervalNetworkSolver
        bypassing the creation of default bounds."""
        solver = AllenIntervalNetworkSolver(0, 200)
        intervals = solver.create_variables(3)

        problem_bounds = Bounds(5, APSPSolver.INF)

        con1 = AllenIntervalConstraint(Type.During, problem_bounds, problem_bounds)
        con1.from_ = intervals[0]
        con1.to = intervals[1]

        con2 = AllenIntervalConstraint(Type.At, Bounds(0, 0), Bounds(100, 100))
        con2.from_ = intervals[1]
        con2.to = intervals[1]

        assert solver.add_constraints(con1, con2) is True

        assert intervals[0].est == 5
        assert intervals[0].lst == 95
        assert intervals[0].eet == 5
        assert intervals[0].let == 95

        assert intervals[1].est == 0
        assert intervals[1].lst == 0
        assert intervals[1].eet == 100
        assert intervals[1].let == 100

    def test_no_default_bounds_on_activity_network_solver(self):
        """The same bug-regression test, but for ActivityNetworkSolver
        (which creates AllenIntervals internally as part of its
        SymbolicVariableActivity)."""
        solver = ActivityNetworkSolver(0, 200)
        solver.create_variables(2)

        intervals = [solver.get_variable(0), solver.get_variable(1)]

        problem_bounds = Bounds(5, APSPSolver.INF)

        con1 = AllenIntervalConstraint(Type.During, problem_bounds, problem_bounds)
        con1.from_ = intervals[0]
        con1.to = intervals[1]

        con2 = AllenIntervalConstraint(Type.At, Bounds(0, 0), Bounds(100, 100))
        con2.from_ = intervals[1]
        con2.to = intervals[1]

        assert solver.add_constraints(con1, con2) is True

        assert intervals[0].temporal_variable.est == 5
        assert intervals[0].temporal_variable.lst == 95
        assert intervals[0].temporal_variable.eet == 5
        assert intervals[0].temporal_variable.let == 95

        assert intervals[1].temporal_variable.est == 0
        assert intervals[1].temporal_variable.lst == 0
        assert intervals[1].temporal_variable.eet == 100
        assert intervals[1].temporal_variable.let == 100
