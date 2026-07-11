"""Port of examples/TestAPSPSolverSimple.java."""

from __future__ import annotations

from metacsp.time import APSPSolver, SimpleDistanceConstraint


def main() -> None:
    solver = APSPSolver(100, 500)

    one, two = solver.create_variables(2)

    con1 = SimpleDistanceConstraint()
    con1.from_ = solver.get_variable(0)
    con1.to = one
    con1.minimum = 60
    con1.maximum = 65

    con3 = SimpleDistanceConstraint()
    con3.from_ = solver.get_variable(0)
    con3.to = two
    con3.minimum = 70
    con3.maximum = 75

    print(f"Adding constraint {con1}...")
    print(solver.add_constraint(con1))

    print(f"Adding constraint {con3}...")
    print(solver.add_constraint(con3))

    con2 = SimpleDistanceConstraint()
    con2.from_ = two
    con2.to = one
    con2.minimum = 2
    con2.maximum = 100

    print(f"Adding constraint {con2}...")
    print(solver.add_constraint(con2))

    solver.remove_constraints([con1, con3])
    print("Removed constraints...")

    print("Re-adding constraints (1):", solver.add_constraints(con1, con3))


if __name__ == "__main__":
    main()
