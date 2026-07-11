"""Port of the ``framework/meta/`` package: meta-CSP variable/constraint/
solver abstractions for backtracking search over implicit meta-variables and
meta-constraints (M4)."""

from metacsp.framework.meta.focus_constraint import FocusConstraint
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.framework.meta.meta_variable import MetaVariable
from metacsp.framework.meta.multi_meta_constraint import MultiMetaConstraint
from metacsp.framework.meta.null_constraint_network import NullConstraintNetwork

__all__ = [
    "FocusConstraint",
    "MetaConstraint",
    "MetaConstraintSolver",
    "MetaVariable",
    "MultiMetaConstraint",
    "NullConstraintNetwork",
]
