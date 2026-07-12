"""Port of tests/multi/TestAllenIntervalNetworkSolver.java."""

from __future__ import annotations

from metacsp.multi.allen_interval import AllenIntervalConstraint, AllenIntervalNetworkSolver
from metacsp.time import Bounds

Type = AllenIntervalConstraint.Type


class TestAllenIntervalNetworkSolver:
    def test_consistency(self):
        solver = AllenIntervalNetworkSolver(0, 100)
        intervals = solver.create_variables(3)

        con1 = AllenIntervalConstraint(Type.During, *Type.During.get_default_bounds())
        con1.from_ = intervals[0]
        con1.to = intervals[1]

        con2 = AllenIntervalConstraint(Type.Duration, Bounds(30, 40))
        con2.from_ = intervals[0]
        con2.to = intervals[0]

        con3 = AllenIntervalConstraint(Type.Overlaps, *Type.Overlaps.get_default_bounds())
        con3.from_ = intervals[1]
        con3.to = intervals[2]

        assert solver.add_constraints(con1, con2, con3) is True

        assert intervals[2].est == 1
        assert intervals[2].lst == 98
        assert intervals[2].eet == 33
        assert intervals[2].let == 100

        assert intervals[1].est == 0
        assert intervals[1].lst == 67
        assert intervals[1].eet == 32
        assert intervals[1].let == 99

        assert intervals[0].est == 1
        assert intervals[0].lst == 68
        assert intervals[0].eet == 31
        assert intervals[0].let == 98
