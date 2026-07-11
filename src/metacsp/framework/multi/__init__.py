"""Port of the ``framework/multi/`` package: MultiVariable/MultiConstraint
machinery for aggregating lower-level constraint networks into higher-level
ones (M3)."""

from metacsp.framework.multi.multi_binary_constraint import MultiBinaryConstraint
from metacsp.framework.multi.multi_constraint import MultiConstraint
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.framework.multi.multi_domain import MultiDomain
from metacsp.framework.multi.multi_variable import MultiVariable

__all__ = [
    "MultiBinaryConstraint",
    "MultiConstraint",
    "MultiConstraintSolver",
    "MultiDomain",
    "MultiVariable",
]
