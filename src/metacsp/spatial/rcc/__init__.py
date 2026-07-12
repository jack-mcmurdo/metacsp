"""Port of the ``spatial/RCC/`` package: RCC-8 (Region Connection Calculus)
constraints and their path-consistency solver (M11)."""

from metacsp.spatial.rcc.rcc_constraint import RCCConstraint
from metacsp.spatial.rcc.rcc_constraint_solver import RCCConstraintSolver
from metacsp.spatial.rcc.rectangle import Rectangle
from metacsp.spatial.rcc.region import Region

__all__ = [
    "RCCConstraint",
    "RCCConstraintSolver",
    "Rectangle",
    "Region",
]
