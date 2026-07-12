"""Port of examples/multi/TestDistanceConstraintSolver.java."""

from __future__ import annotations

from metacsp.framework.multi import MultiConstraint
from metacsp.multi.tcsp import DistanceConstraint, DistanceConstraintSolver
from metacsp.time import APSPSolver, Bounds


def main() -> None:
    ground_solver = DistanceConstraintSolver(0, 100)

    # John travels to work either by car (30-40 min) or by bus (at least 60 min).
    # Fred goes to work either by car (20-30 min) or in a carpool (40-50 min).
    # Today John left home between 7:10 and 7:20 AM, and Fred arrived at work
    # between 8:00 and 8:10 AM. John arrived at work 10-20 min after Fred left home.

    john_goes_to_work = ground_solver.create_variable()
    john_arrives_at_work = ground_solver.create_variable()
    fred_goes_to_work = ground_solver.create_variable()
    fred_arrives_at_work = ground_solver.create_variable()

    john_takes_bus = DistanceConstraint(Bounds(60, APSPSolver.INF))
    john_takes_bus.from_ = john_goes_to_work
    john_takes_bus.to = john_arrives_at_work

    fred_takes_carpool = DistanceConstraint(Bounds(40, 50))
    fred_takes_carpool.from_ = fred_goes_to_work
    fred_takes_carpool.to = fred_arrives_at_work

    john_leaves = DistanceConstraint(Bounds(10, 20))
    john_leaves.from_ = ground_solver.get_source()
    john_leaves.to = john_goes_to_work

    fred_arrives = DistanceConstraint(Bounds(60, 70))
    fred_arrives.from_ = ground_solver.get_source()
    fred_arrives.to = fred_arrives_at_work

    john_arrives = DistanceConstraint(Bounds(10, 20))
    john_arrives.from_ = john_arrives_at_work
    john_arrives.to = fred_goes_to_work

    # THIS LABELING DOES NOT WORK (per the Java original's comment)
    ground_solver.add_constraint(john_takes_bus)
    ground_solver.add_constraint(fred_takes_carpool)

    ground_solver.add_constraint(john_leaves)
    ground_solver.add_constraint(fred_arrives)
    ground_solver.add_constraint(john_arrives)

    for c in ground_solver.get_constraints():
        if isinstance(c, MultiConstraint):
            print(c, "(prop =", c.propagate_immediately(), ")")

    print(ground_solver.description)
    print(fred_goes_to_work.description)


if __name__ == "__main__":
    main()
