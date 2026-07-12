"""Port of the ``multi/spatioTemporal/`` package: SpatioTemporalVariable and
its constraint solver, combining an Allen-interval temporal part with a
DE-9IM geometric spatial part (M14)."""

from metacsp.multi.spatio_temporal.spatio_temporal_variable import SpatioTemporalVariable
from metacsp.multi.spatio_temporal.spatio_temporal_variable_solver import (
    SpatioTemporalVariableSolver,
)

__all__ = [
    "SpatioTemporalVariable",
    "SpatioTemporalVariableSolver",
]
