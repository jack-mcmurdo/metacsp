"""Port of examples/multi/TestAllenIntervalNetworkSolver.java.

The Java original draws the constraint network (``ConstraintNetwork.draw``,
Swing -- not ported, see D10); dropped here.
"""

from __future__ import annotations

from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.time.bounds import Bounds


def main() -> None:
    solver = AllenIntervalNetworkSolver(0, 100)
    intervals = solver.create_variables(3)
    assert intervals is not None

    con1 = AllenIntervalConstraint(AllenIntervalConstraint.Type.During)
    con1.from_ = intervals[0]
    con1.to = intervals[1]

    con2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Duration, Bounds(30, 40))
    con2.from_ = intervals[0]
    con2.to = intervals[0]

    con3 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Overlaps)
    con3.from_ = intervals[1]
    con3.to = intervals[2]

    print(solver.add_constraints_debug(con1, con2, con3) is None)

    con4 = AllenIntervalConstraint(AllenIntervalConstraint.Type.After)
    con4.from_ = intervals[0]
    con4.to = intervals[2]

    print("FOR JASMIN:", solver.add_constraint(con4))


if __name__ == "__main__":
    main()
