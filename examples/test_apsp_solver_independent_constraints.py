"""Port of examples/TestAPSPSolverIndependentConstraints.java."""

from __future__ import annotations

from metacsp.time import APSPSolver, SimpleDistanceConstraint


def main() -> None:
    solver = APSPSolver(0, 100, 10)
    vars_ = solver.create_variables(4)

    con1 = SimpleDistanceConstraint()
    con1.from_ = vars_[0]
    con1.to = vars_[1]
    con1.minimum = 0
    con1.maximum = APSPSolver.INF

    con2 = SimpleDistanceConstraint()
    con2.from_ = vars_[2]
    con2.to = vars_[3]
    con2.minimum = 0
    con2.maximum = APSPSolver.INF

    print(solver.print_dist())

    solver.add_constraints(con1, con2)

    print("-------------------")
    print(solver.print_dist())

    print("AAAAAAAAAAA")

    solver = APSPSolver(0, 100, 10)
    vars_ = solver.create_variables(4)

    con1 = SimpleDistanceConstraint()
    con1.from_ = vars_[0]
    con1.to = vars_[1]
    con1.minimum = 0
    con1.maximum = APSPSolver.INF

    con2 = SimpleDistanceConstraint()
    con2.from_ = vars_[2]
    con2.to = vars_[3]
    con2.minimum = 0
    con2.maximum = APSPSolver.INF

    print(solver.print_dist())

    solver.set_adding_independent_constraints()
    solver.add_constraints(con1, con2)

    print("-------------------")
    print(solver.print_dist())


if __name__ == "__main__":
    main()
