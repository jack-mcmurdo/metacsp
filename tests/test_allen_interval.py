"""Port of tests/multi/TestAllenInterval.java.

``testNoDefaultBoundsOnActivityNetworkSolver`` is deferred until
ActivityNetworkSolver lands (it needs multi/symbols + booleanSAT first; see
PLAN.md's M6/M7/M8 ordering note).
"""

from __future__ import annotations

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
