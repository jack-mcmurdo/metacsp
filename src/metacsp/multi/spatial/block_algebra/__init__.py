"""Port of the ``multi/spatial/blockAlgebra/`` package: Block Algebra --
axis-parallel cuboids reasoned about as a triple of Allen intervals (one per
axis) -- and its constraint solver (M13)."""

from metacsp.multi.spatial.block_algebra.block_algebra_constraint import BlockAlgebraConstraint
from metacsp.multi.spatial.block_algebra.block_constraint_solver import BlockConstraintSolver
from metacsp.multi.spatial.block_algebra.rectangular_cuboid import RectangularCuboid
from metacsp.multi.spatial.block_algebra.rectangular_cuboid_region import RectangularCuboidRegion
from metacsp.multi.spatial.block_algebra.unary_block_constraint import UnaryBlockConstraint

__all__ = [
    "BlockAlgebraConstraint",
    "BlockConstraintSolver",
    "RectangularCuboid",
    "RectangularCuboidRegion",
    "UnaryBlockConstraint",
]
