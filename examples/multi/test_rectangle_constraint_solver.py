"""Port of examples/multi/TestRectangleConstraintSolver.java.

The Java original ends with ``ConstraintNetwork.draw(...)`` (Swing, not
ported -- see D10); dropped here. The ``drawAlmostCentreRectangle(...)``
Gnuplot-script print is kept.
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
    knife = solver.create_variable()
    assert isinstance(knife, RectangularRegion)
    knife.name = "knife"

    fork = solver.create_variable()
    assert isinstance(fork, RectangularRegion)
    fork.name = "fork"

    dish = solver.create_variable()
    assert isinstance(dish, RectangularRegion)
    dish.name = "dish"

    cup = solver.create_variable()
    assert isinstance(cup, RectangularRegion)
    cup.name = "cup"

    napkin = solver.create_variable()
    assert isinstance(napkin, RectangularRegion)
    napkin.name = "napkin"

    # ..........................................................
    # A-BOX Variables and constraints
    napkin1 = solver.create_variable()
    assert isinstance(napkin1, RectangularRegion)
    napkin1.name = "napkin1"
    # No need for a unary constraint here, the bounds will be [0,infty) anyway.

    knife1 = solver.create_variable()
    assert isinstance(knife1, RectangularRegion)
    knife1.name = "knife1"
    at_knife1 = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(50, 50),
        Bounds(55, 55),
        Bounds(12, 12),
        Bounds(26, 26),
    )
    at_knife1.from_ = knife1
    at_knife1.to = knife1
    all_constraints.append(at_knife1)

    fork1 = solver.create_variable()
    assert isinstance(fork1, RectangularRegion)
    fork1.name = "fork1"
    at_fork1 = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(5, 5),
        Bounds(10, 10),
        Bounds(14, 14),
        Bounds(24, 24),
    )
    at_fork1.from_ = fork1
    at_fork1.to = fork1
    all_constraints.append(at_fork1)

    dish1 = solver.create_variable()
    assert isinstance(dish1, RectangularRegion)
    dish1.name = "dish1"

    cup1 = solver.create_variable()
    assert isinstance(cup1, RectangularRegion)
    cup1.name = "cup1"
    at_cup1 = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(20, 20),
        Bounds(28, 28),
        Bounds(35, 35),
        Bounds(42, 42),
    )
    at_cup1.from_ = cup1
    at_cup1.to = cup1
    all_constraints.append(at_cup1)

    # ..........................................................
    # T-BOX Constraints
    size_dish = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.Size, Bounds(10, 20), Bounds(10, 20)
    )
    size_dish.from_ = dish1
    size_dish.to = dish1
    all_constraints.append(size_dish)

    cup_to_dish = RectangleConstraint(
        AllenIntervalConstraint(
            AllenIntervalConstraint.Type.During, AllenIntervalConstraint.Type.OverlappedBy
        ),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.After),
    )
    cup_to_dish.from_ = cup
    cup_to_dish.to = dish
    all_constraints.append(cup_to_dish)

    knife_to_dish = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.After, Bounds(4, 10)),
        AllenIntervalConstraint(
            AllenIntervalConstraint.Type.During,
            *AllenIntervalConstraint.Type.During.get_default_bounds(),
        ),
    )
    knife_to_dish.from_ = knife
    knife_to_dish.to = dish
    all_constraints.append(knife_to_dish)

    fork_to_dish = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Before),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.During),
    )
    fork_to_dish.from_ = fork
    fork_to_dish.to = dish
    all_constraints.append(fork_to_dish)

    # ..........................................................
    # A-BOX to T-BOX Constraints
    napkin_assertion = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
    )
    napkin_assertion.from_ = napkin1
    napkin_assertion.to = napkin
    all_constraints.append(napkin_assertion)

    cup_assertion = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
    )
    cup_assertion.from_ = cup
    cup_assertion.to = cup1
    all_constraints.append(cup_assertion)

    knife_assertion = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
    )
    knife_assertion.from_ = knife
    knife_assertion.to = knife1
    all_constraints.append(knife_assertion)

    fork_assertion = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
    )
    fork_assertion.from_ = fork
    fork_assertion.to = fork1
    all_constraints.append(fork_assertion)

    dish_assertion = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
    )
    dish_assertion.from_ = dish
    dish_assertion.to = dish1
    all_constraints.append(dish_assertion)

    if not solver.add_constraints(*all_constraints):
        print("Failed to add constraints!")
        return

    print(solver.draw_almost_centre_rectangle(100, dish))


if __name__ == "__main__":
    main()
