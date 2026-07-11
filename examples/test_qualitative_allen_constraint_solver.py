"""Port of examples/TestQualitativeAllenConstraintSolver.java.

The Java original draws the resulting network (Swing, not ported -- see D10).
"""

from __future__ import annotations

import sys

from metacsp.time.qualitative import QualitativeAllenIntervalConstraint, QualitativeAllenSolver

Type = QualitativeAllenIntervalConstraint.Type


def main() -> None:
    solver = QualitativeAllenSolver()
    re0, re1, re2 = solver.create_variables(3)

    con0 = QualitativeAllenIntervalConstraint(Type.Before, Type.Meets)
    con0.from_ = re0
    con0.to = re1

    con1 = QualitativeAllenIntervalConstraint(Type.After)
    con1.from_ = re1
    con1.to = re2

    con2 = QualitativeAllenIntervalConstraint(Type.Finishes)
    con2.from_ = re2
    con2.to = re0

    if not solver.add_constraints(con0, con1, con2):
        print("Failed to add constraints!")
        sys.exit(0)

    print(solver.constraint_network)


if __name__ == "__main__":
    main()
