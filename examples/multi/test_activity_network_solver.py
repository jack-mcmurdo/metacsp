"""Port of examples/multi/TestActivityNetworkSolver.java.

The Java original draws the constraint network (``ConstraintNetwork.draw``,
Swing -- not ported, see D10); dropped here.
"""

from __future__ import annotations

from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.time.bounds import Bounds


def main() -> None:
    solver = ActivityNetworkSolver(0, 500, ["A", "B", "C", "D", "E", "F"])
    act1 = solver.create_variable()
    assert isinstance(act1, SymbolicVariableActivity)
    act1.set_symbolic_domain("A", "B", "C")
    act2 = solver.create_variable()
    assert isinstance(act2, SymbolicVariableActivity)
    act2.set_symbolic_domain("B", "C", "D")

    con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
    con1.set_from(act1)
    con1.set_to(act2)

    con1a = SymbolicValueConstraint(SymbolicValueConstraint.Type.VALUESUBSET)
    con1a.set_from(act1)
    con1a.set_to(act1)
    con1a.value = ["B", "C"]

    con2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Before, Bounds(10, 20))
    con2.from_ = act1
    con2.to = act2

    con3 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Duration, Bounds(5, 5))
    con3.from_ = act1
    con3.to = act1

    con4 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Duration, Bounds(5, 5))
    con4.from_ = act2
    con4.to = act2

    con5 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(13, solver.horizon))
    con5.from_ = act2
    con5.to = act2

    con5a = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Release, Bounds(13, solver.horizon)
    )
    con5a.from_ = act2
    con5a.to = act2

    print(solver.add_constraints(con1, con1a, con2, con3, con4, con5, con5a))


if __name__ == "__main__":
    main()
