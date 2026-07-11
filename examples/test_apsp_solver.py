"""Port of examples/TestAPSPSolver.java.

The Java original draws the network (Swing, not ported -- see D10) and then
loops forever, alternately adding/removing a constraint and printing the
network's RMS rigidity every 2 seconds. Here the loop runs a fixed, short
number of iterations so the script exits cleanly.
"""

from __future__ import annotations

from metacsp.time import APSPSolver, SimpleDistanceConstraint


def main() -> None:
    solver = APSPSolver(100, 500)

    one, two, three = solver.create_variables(3)

    con1 = SimpleDistanceConstraint()
    con1.from_ = solver.get_variable(0)
    con1.to = one
    con1.minimum = 60
    con1.maximum = 75

    con2 = SimpleDistanceConstraint()
    con2.from_ = one
    con2.to = two
    con2.minimum = 7
    con2.maximum = 9

    con3 = SimpleDistanceConstraint()
    con3.from_ = solver.get_variable(0)
    con3.to = two
    con3.minimum = 68
    con3.maximum = 70

    print(solver.add_constraints(con1, con2, con3))

    con4 = SimpleDistanceConstraint()
    con4.from_ = two
    con4.to = three
    con4.minimum = 56
    con4.maximum = 100
    print(solver.add_constraint(con4))

    con5 = SimpleDistanceConstraint()
    con5.from_ = one
    con5.to = three
    con5.minimum = 70
    con5.maximum = 100
    solver.add_constraint(con5)

    for _ in range(3):
        solver.add_constraint(con5)
        print("Rigidity:", solver.get_rms_rigidity())

        solver.remove_constraint(con2)
        print("Rigidity:", solver.get_rms_rigidity())

        solver.remove_constraint(con5)
        print("Rigidity:", solver.get_rms_rigidity())

        solver.add_constraint(con2)
        print("Rigidity:", solver.get_rms_rigidity())


if __name__ == "__main__":
    main()
