"""Port of examples/meta/TestTCSPSolver.java.

The Java original draws the TCSP/STP networks (Swing ``ConstraintNetwork.draw``,
not ported -- see D10); those calls are dropped here.

John travels to work either by car (30-40 min) or by bus (at least 60 min).
Fred goes to work either by car (20-30 min) or in a carpool (40-50 min).
Today John left home between 7:10 and 7:20 AM, and Fred arrived at work
between 8:00 and 8:10 AM. John arrived at work 10-20 min after Fred left home.
"""

from __future__ import annotations

from metacsp.meta.tcsp import (
    MostConstrainedFirstVarOH,
    TCSPLabeling,
    TCSPSolver,
    WidestIntervalFirstValOH,
)
from metacsp.multi.tcsp.distance_constraint import DistanceConstraint
from metacsp.multi.tcsp.distance_constraint_solver import DistanceConstraintSolver
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds


def main() -> None:
    meta_solver = TCSPSolver(0, 100, 0)
    ground_solver = meta_solver.constraint_solvers[0]
    assert isinstance(ground_solver, DistanceConstraintSolver)

    john_goes_to_work = ground_solver.create_variable()
    john_arrives_at_work = ground_solver.create_variable()
    fred_goes_to_work = ground_solver.create_variable()
    fred_arrives_at_work = ground_solver.create_variable()

    john_takes_car_or_bus = DistanceConstraint(Bounds(30, 40), Bounds(60, APSPSolver.INF))
    john_takes_car_or_bus.from_ = john_goes_to_work
    john_takes_car_or_bus.to = john_arrives_at_work

    fred_takes_car_or_carpool = DistanceConstraint(Bounds(40, 50), Bounds(20, 30))
    fred_takes_car_or_carpool.from_ = fred_goes_to_work
    fred_takes_car_or_carpool.to = fred_arrives_at_work

    john_leaves = DistanceConstraint(Bounds(10, 20))
    john_leaves.from_ = ground_solver.source
    john_leaves.to = john_goes_to_work

    fred_arrives = DistanceConstraint(Bounds(60, 70))
    fred_arrives.from_ = ground_solver.source
    fred_arrives.to = fred_arrives_at_work

    john_arrives = DistanceConstraint(Bounds(10, 20))
    john_arrives.from_ = john_arrives_at_work
    john_arrives.to = fred_goes_to_work

    ground_solver.add_constraints(
        john_takes_car_or_bus,
        fred_takes_car_or_carpool,
        john_leaves,
        fred_arrives,
        john_arrives,
    )

    var_oh = MostConstrainedFirstVarOH()
    val_oh = WidestIntervalFirstValOH()

    meta_cons = TCSPLabeling(var_oh, val_oh)
    meta_solver.add_meta_constraint(meta_cons)

    print("Solved?", meta_solver.backtrack())

    print(meta_solver.description)
    print(meta_cons.description)


if __name__ == "__main__":
    main()
