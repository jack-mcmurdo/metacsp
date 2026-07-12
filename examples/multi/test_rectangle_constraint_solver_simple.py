"""Port of examples/multi/TestRectangleConstraintSolverSimple.java.

The Java original ends with ``ConstraintNetwork.draw(...)`` and a
``Thread.sleep(2000)`` (Swing, not ported -- see D10); dropped here. The
final ``solver.removeConstraint(varAooVarC)`` call is kept.
"""

from __future__ import annotations

from metacsp.multi.allen_interval import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra import (
    RectangleConstraint,
    RectangleConstraintSolver,
    RectangularRegion,
    UnaryRectangleConstraint,
)
from metacsp.time.bounds import Bounds


def main() -> None:
    solver = RectangleConstraintSolver(0, 1000)
    all_constraints = []

    # ..........................................................
    # T-BOX Variables
    var_a = solver.create_variable()
    assert isinstance(var_a, RectangularRegion)
    var_a.name = "A"

    var_b = solver.create_variable()
    assert isinstance(var_b, RectangularRegion)
    var_b.name = "B"

    var_c = solver.create_variable()
    assert isinstance(var_c, RectangularRegion)
    var_c.name = "C"

    # ..........................................................
    at_a = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(50, 50),
        Bounds(55, 55),
        Bounds(12, 12),
        Bounds(26, 26),
    )
    at_a.from_ = var_a
    at_a.to = var_a
    all_constraints.append(at_a)

    at_b = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(5, 5),
        Bounds(10, 10),
        Bounds(14, 14),
        Bounds(24, 24),
    )
    at_b.from_ = var_b
    at_b.to = var_b
    all_constraints.append(at_b)

    var_a_oo_var_c = RectangleConstraint(
        AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Overlaps,
            *AllenIntervalConstraint.Type.Overlaps.get_default_bounds(),
        ),
        AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Overlaps,
            *AllenIntervalConstraint.Type.Overlaps.get_default_bounds(),
        ),
    )
    var_a_oo_var_c.from_ = var_a
    var_a_oo_var_c.to = var_c
    all_constraints.append(var_a_oo_var_c)

    if not solver.add_constraints(*all_constraints):
        print("Failed to add constraints!")
        return

    solver.remove_constraint(var_a_oo_var_c)


if __name__ == "__main__":
    main()
