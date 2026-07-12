"""Port of tests/multi/TestActivityNetworkSolver.java."""

from __future__ import annotations

from metacsp.multi.activity import ActivityNetworkSolver
from metacsp.multi.allen_interval import AllenIntervalConstraint
from metacsp.multi.symbols import SymbolicValueConstraint
from metacsp.time import Bounds

Type = AllenIntervalConstraint.Type


class TestActivityNetworkSolver:
    def test_consistency(self):
        solver = ActivityNetworkSolver(0, 500, ["A", "B", "C", "D", "E", "F"])
        act1 = solver.create_variable()
        act1.set_symbolic_domain("A", "B", "C")
        act2 = solver.create_variable()
        act2.set_symbolic_domain("B", "C")

        con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
        con1.set_from(act1)
        con1.set_to(act2)

        con2 = AllenIntervalConstraint(Type.Before, Bounds(10, 20))
        con2.from_ = act1
        con2.to = act2

        con3 = AllenIntervalConstraint(Type.Duration, Bounds(5, 5))
        con3.from_ = act1
        con3.to = act1

        con4 = AllenIntervalConstraint(Type.Duration, Bounds(5, 5))
        con4.from_ = act2
        con4.to = act2

        con5 = AllenIntervalConstraint(Type.Release, Bounds(13, solver.horizon))
        con5.from_ = act2
        con5.to = act2

        con5a = AllenIntervalConstraint(Type.Release, Bounds(13, solver.horizon))
        con5a.from_ = act2
        con5a.to = act2

        assert solver.add_constraints(con1, con2, con3, con4, con5, con5a) is True

        assert act1.temporal_variable.est == 0
        assert act1.temporal_variable.lst == 480
        assert act1.temporal_variable.eet == 5
        assert act1.temporal_variable.let == 485

        assert act2.temporal_variable.est == 15
        assert act2.temporal_variable.lst == 495
        assert act2.temporal_variable.eet == 20
        assert act2.temporal_variable.let == 500
