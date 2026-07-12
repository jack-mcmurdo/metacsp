"""Port of examples/multi/TestBlockAlgebraConstraintSolverSimple.java.

The Java original ends with ``ConstraintNetwork.draw(...)`` (Swing, not
ported -- see D10); dropped here.
"""

from __future__ import annotations

from metacsp.multi.allen_interval import AllenIntervalConstraint
from metacsp.multi.spatial.block_algebra import (
    BlockAlgebraConstraint,
    BlockConstraintSolver,
    RectangularCuboidRegion,
    UnaryBlockConstraint,
)
from metacsp.time.bounds import Bounds


def main() -> None:
    solver = BlockConstraintSolver(0, 1000)
    all_constraints = []

    # ..........................................................
    block1 = solver.create_variable()
    assert isinstance(block1, RectangularCuboidRegion)
    block1.name = "block1"

    block2 = solver.create_variable()
    assert isinstance(block2, RectangularCuboidRegion)
    block2.name = "block2"

    on_top_of_each_other = BlockAlgebraConstraint(
        AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Equals,
            *AllenIntervalConstraint.Type.Equals.get_default_bounds(),
        ),
        AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Equals,
            *AllenIntervalConstraint.Type.Equals.get_default_bounds(),
        ),
        AllenIntervalConstraint(
            AllenIntervalConstraint.Type.MetBy,
            *AllenIntervalConstraint.Type.MetBy.get_default_bounds(),
        ),
    )
    on_top_of_each_other.from_ = block1
    on_top_of_each_other.to = block2
    all_constraints.append(on_top_of_each_other)

    at_block2 = UnaryBlockConstraint(
        UnaryBlockConstraint.Type.At,
        Bounds(20, 20),
        Bounds(28, 28),
        Bounds(35, 35),
        Bounds(42, 42),
        Bounds(0, 0),
        Bounds(20, 20),
    )
    at_block2.from_ = block2
    at_block2.to = block2
    all_constraints.append(at_block2)

    size_block1 = UnaryBlockConstraint(
        UnaryBlockConstraint.Type.Size, Bounds(8, 8), Bounds(7, 7), Bounds(30, 30)
    )
    size_block1.from_ = block1
    size_block1.to = block1
    all_constraints.append(size_block1)

    if not solver.add_constraints(*all_constraints):
        print("Failed to add constraints!")
        return

    print(solver.extract_bounding_boxes_from_stps("block1").get_almost_centre_rec_cuboid())


if __name__ == "__main__":
    main()
