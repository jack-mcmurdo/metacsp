"""Tests for metacsp.multi.spatial.rectangle_algebra, block_algebra, and
metacsp.multi.temporal_rectangle_algebra.

The Java examples this module ports (TestRectangleConstraintSolverSimple,
TestRectangleConstraintSolver, TestBlockAlgebraConstraintSolverSimple) are
``main()`` methods, not JUnit tests -- they contain no ``assert`` statements,
only a "Failed to add constraints!" print/exit(0) on the one condition they
do check (``solver.addConstraints(...)``). The tests below assert that same
condition (constraint addition succeeds) for each ported example's exact
scenario, plus the resulting bounding boxes -- computed deterministically by
running our own port (there is no Java assertion oracle for the specific
numeric bounds), which is reasonable given every constraint below is either
a fully pinning ``At``/``Equals`` constraint or derives deterministically
from one.

``SpatialFluentSolver``/``SpatialFluentSolver2`` (multi_temporal_rectangle_
algebra) have no Java example at all (see PLAN.md's M13 notes: their Java
usage is only indirect, inside M18's out-of-scope hybrid-planner examples).
The final test below is a minimal, clearly-commented smoke test of our own
devising, not a ported oracle.
"""

from __future__ import annotations

from metacsp.multi.allen_interval import AllenIntervalConstraint
from metacsp.multi.spatial.block_algebra import (
    BlockAlgebraConstraint,
    BlockConstraintSolver,
    RectangularCuboidRegion,
    UnaryBlockConstraint,
)
from metacsp.multi.spatial.rectangle_algebra import (
    RectangleConstraint,
    RectangleConstraintSolver,
    RectangularRegion,
    UnaryRectangleConstraint,
)
from metacsp.multi.temporal_rectangle_algebra import SpatialFluentSolver
from metacsp.time.bounds import Bounds


def test_rectangle_constraint_solver_simple() -> None:
    """Port of examples/multi/TestRectangleConstraintSolverSimple.java."""
    solver = RectangleConstraintSolver(0, 1000)

    var_a = solver.create_variable()
    assert isinstance(var_a, RectangularRegion)
    var_a.name = "A"
    var_b = solver.create_variable()
    assert isinstance(var_b, RectangularRegion)
    var_b.name = "B"
    var_c = solver.create_variable()
    assert isinstance(var_c, RectangularRegion)
    var_c.name = "C"

    at_a = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(50, 50),
        Bounds(55, 55),
        Bounds(12, 12),
        Bounds(26, 26),
    )
    at_a.from_ = var_a
    at_a.to = var_a

    at_b = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(5, 5),
        Bounds(10, 10),
        Bounds(14, 14),
        Bounds(24, 24),
    )
    at_b.from_ = var_b
    at_b.to = var_b

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

    assert solver.add_constraints(at_a, at_b, var_a_oo_var_c)

    bb_a = solver.extract_bounding_boxes_from_stps("A")
    assert bb_a is not None
    assert (bb_a.x_lb, bb_a.x_ub, bb_a.y_lb, bb_a.y_ub) == (
        Bounds(50, 50),
        Bounds(55, 55),
        Bounds(12, 12),
        Bounds(26, 26),
    )

    bb_b = solver.extract_bounding_boxes_from_stps("B")
    assert bb_b is not None
    assert (bb_b.x_lb, bb_b.x_ub, bb_b.y_lb, bb_b.y_ub) == (
        Bounds(5, 5),
        Bounds(10, 10),
        Bounds(14, 14),
        Bounds(24, 24),
    )

    # C overlaps A on both axes -- deterministic, derived bounds (A's X is
    # pinned to [50,55], its Y to [12,26]; "Overlaps" forces C to start
    # strictly after A starts and end strictly after A ends, up to horizon).
    bb_c = solver.extract_bounding_boxes_from_stps("C")
    assert bb_c is not None
    assert (bb_c.x_lb, bb_c.x_ub, bb_c.y_lb, bb_c.y_ub) == (
        Bounds(51, 54),
        Bounds(56, 1000),
        Bounds(13, 25),
        Bounds(27, 1000),
    )

    # Java's example ends by removing the A-overlaps-C constraint; assert
    # this doesn't raise.
    solver.remove_constraint(var_a_oo_var_c)


def test_rectangle_constraint_solver() -> None:
    """Port of examples/multi/TestRectangleConstraintSolver.java (the
    knife/fork/dish/cup/napkin T-BOX/A-BOX scenario)."""
    solver = RectangleConstraintSolver(0, 1000)
    all_constraints = []

    knife = solver.create_variable()
    fork = solver.create_variable()
    dish = solver.create_variable()
    cup = solver.create_variable()
    napkin = solver.create_variable()
    for v, name in (
        (knife, "knife"),
        (fork, "fork"),
        (dish, "dish"),
        (cup, "cup"),
        (napkin, "napkin"),
    ):
        assert isinstance(v, RectangularRegion)
        v.name = name

    napkin1 = solver.create_variable()
    assert isinstance(napkin1, RectangularRegion)
    napkin1.name = "napkin1"

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

    assertions = [
        (napkin1, napkin),
        (cup, cup1),
        (knife, knife1),
        (fork, fork1),
        (dish, dish1),
    ]
    for from_v, to_v in assertions:
        con = RectangleConstraint(
            AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
            AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
        )
        con.from_ = from_v
        con.to = to_v
        all_constraints.append(con)

    assert solver.add_constraints(*all_constraints)
    assert len(solver.get_variables()) == 10

    bb_knife = solver.extract_bounding_boxes_from_stps("knife")
    assert bb_knife is not None
    assert (bb_knife.x_lb, bb_knife.x_ub, bb_knife.y_lb, bb_knife.y_ub) == (
        Bounds(50, 50),
        Bounds(55, 55),
        Bounds(12, 12),
        Bounds(26, 26),
    )

    bb_fork = solver.extract_bounding_boxes_from_stps("fork")
    assert bb_fork is not None
    assert (bb_fork.x_lb, bb_fork.x_ub, bb_fork.y_lb, bb_fork.y_ub) == (
        Bounds(5, 5),
        Bounds(10, 10),
        Bounds(14, 14),
        Bounds(24, 24),
    )

    bb_dish = solver.extract_bounding_boxes_from_stps("dish")
    assert bb_dish is not None
    assert (bb_dish.x_lb, bb_dish.x_ub, bb_dish.y_lb, bb_dish.y_ub) == (
        Bounds(20, 20),
        Bounds(40, 40),
        Bounds(7, 11),
        Bounds(27, 31),
    )

    bb_cup = solver.extract_bounding_boxes_from_stps("cup")
    assert bb_cup is not None
    assert (bb_cup.x_lb, bb_cup.x_ub, bb_cup.y_lb, bb_cup.y_ub) == (
        Bounds(20, 20),
        Bounds(28, 28),
        Bounds(35, 35),
        Bounds(42, 42),
    )

    # Java's example prints this Gnuplot script; assert it runs clean and
    # produces the expected shape (header/footer + one rect/label pair).
    script = solver.draw_almost_centre_rectangle(100, dish)
    assert script.startswith("set xrange [0:100]\nset yrange [0:100]\n")
    assert script.count("set obj") == 1
    assert script.count("set label") == 1
    assert script.endswith("plot NaN\npause -1")


def test_block_algebra_constraint_solver_simple() -> None:
    """Port of examples/multi/TestBlockAlgebraConstraintSolverSimple.java."""
    solver = BlockConstraintSolver(0, 1000)

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

    size_block1 = UnaryBlockConstraint(
        UnaryBlockConstraint.Type.Size, Bounds(8, 8), Bounds(7, 7), Bounds(30, 30)
    )
    size_block1.from_ = block1
    size_block1.to = block1

    assert solver.add_constraints(on_top_of_each_other, at_block2, size_block1)

    bb1 = solver.extract_bounding_boxes_from_stps("block1")
    assert bb1 is not None
    assert (bb1.x_lb, bb1.x_ub, bb1.y_lb, bb1.y_ub, bb1.z_lb, bb1.z_ub) == (
        Bounds(20, 20),
        Bounds(28, 28),
        Bounds(35, 35),
        Bounds(42, 42),
        Bounds(20, 20),  # block1 sits atop block2 (whose Z is [0,20]) -> Z starts at 20
        Bounds(50, 50),  # ... and has depth 30 (the Size constraint) -> ends at 50
    )

    bb2 = solver.extract_bounding_boxes_from_stps("block2")
    assert bb2 is not None
    assert (bb2.x_lb, bb2.x_ub, bb2.y_lb, bb2.y_ub, bb2.z_lb, bb2.z_ub) == (
        Bounds(20, 20),
        Bounds(28, 28),
        Bounds(35, 35),
        Bounds(42, 42),
        Bounds(0, 0),
        Bounds(20, 20),
    )

    # Java's example prints this cuboid's toString(); assert it matches
    # exactly (including the upstream "lenght"/missing-"width:" typos --
    # this printed string is directly observed by the ported example, so
    # matching it exactly is part of replicating Java's observable output).
    cuboid = bb1.get_almost_centre_rec_cuboid()
    assert str(cuboid) == "[x: 20.0, y: 35.0, z: 20.0, lenght: 8, : 7, height: 30]"


def test_spatial_fluent_solver_smoke() -> None:
    """Minimal smoke test for SpatialFluentSolver -- no Java example exists
    for this class (see this module's docstring and PLAN.md's M13 notes).

    Builds two SpatialFluents and pins/relates their spatial (Rectangle
    Algebra) component through the RectangleConstraintSolver that
    SpatialFluentSolver composes internally, then checks the result is
    sane: no crash, constraints accepted, and the resulting bounding boxes
    are exactly what the constraints demand.

    (Routing a RectangleConstraint through SpatialFluentSolver's own
    top-level add_constraints -- with scope directly on the SpatialFluents,
    rather than on their inner RectangularRegions as done here -- exercises
    a generic MultiConstraintSolver code path whose index-based bookkeeping
    assumes constraint_types and constraint_solvers are the same length;
    SpatialFluentSolver's Java constructor registers 5 constraint types
    over only 3 internal solvers, same as here, so that path is
    structurally fragile in both languages and is only ever exercised
    indirectly, deep inside M18's hybrid planner -- out of scope for this
    smoke test.)
    """
    solver = SpatialFluentSolver(0, 1000)
    fluents = solver.create_variables(2)
    assert fluents is not None and len(fluents) == 2
    f1, f2 = fluents

    # Each SpatialFluent exposes its 3 internal variables through typed
    # accessors without raising.
    assert f1.rectangular_region is not None
    assert f1.activity is not None
    assert f1.configuration_variable is not None

    rect_solver = solver.constraint_solvers[0]
    assert isinstance(rect_solver, RectangleConstraintSolver)

    at_f1 = UnaryRectangleConstraint(
        UnaryRectangleConstraint.Type.At,
        Bounds(10, 10),
        Bounds(20, 20),
        Bounds(5, 5),
        Bounds(15, 15),
    )
    at_f1.from_ = f1.rectangular_region
    at_f1.to = f1.rectangular_region

    eq = RectangleConstraint(
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
        AllenIntervalConstraint(AllenIntervalConstraint.Type.Equals),
    )
    eq.from_ = f1.rectangular_region
    eq.to = f2.rectangular_region

    assert rect_solver.add_constraints(at_f1, eq)

    bb1 = rect_solver.extract_bounding_boxes_from_stps(f1.rectangular_region)
    bb2 = rect_solver.extract_bounding_boxes_from_stps(f2.rectangular_region)
    assert bb1 is not None and bb2 is not None
    expected = (Bounds(10, 10), Bounds(20, 20), Bounds(5, 5), Bounds(15, 15))
    assert (bb1.x_lb, bb1.x_ub, bb1.y_lb, bb1.y_ub) == expected
    assert (bb2.x_lb, bb2.x_ub, bb2.y_lb, bb2.y_ub) == expected
