"""Port of the ``fuzzyAllenInterval/`` package: fuzzy Allen interval
constraints and fuzzy path consistency (M9)."""

from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_network_solver import (
    FuzzyAllenIntervalNetworkSolver,
)

__all__ = ["FuzzyAllenIntervalConstraint", "FuzzyAllenIntervalNetworkSolver"]
