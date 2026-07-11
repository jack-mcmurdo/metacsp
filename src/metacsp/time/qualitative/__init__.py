"""Port of the ``time/qualitative/`` package: path-consistency solving for
disjunctive (qualitative) Allen interval constraints (M5)."""

from metacsp.time.qualitative.qualitative_allen_interval_constraint import (
    QualitativeAllenIntervalConstraint,
)
from metacsp.time.qualitative.qualitative_allen_solver import QualitativeAllenSolver
from metacsp.time.qualitative.simple_allen_interval import SimpleAllenInterval
from metacsp.time.qualitative.simple_interval import SimpleInterval

__all__ = [
    "QualitativeAllenIntervalConstraint",
    "QualitativeAllenSolver",
    "SimpleAllenInterval",
    "SimpleInterval",
]
