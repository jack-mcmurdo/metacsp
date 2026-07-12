"""Port of multi/allenInterval/AllenIntervalNetworkUtilities.java."""

from __future__ import annotations

from typing import cast

from metacsp.framework.constraint import Constraint
from metacsp.framework.variable import Variable
from metacsp.multi.allen_interval.allen_interval import AllenInterval
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.simple_distance_constraint import SimpleDistanceConstraint
from metacsp.time.time_point import TimePoint
from metacsp.utility.logging import get_logger

__all__ = ["clone", "create_reduced_copy"]

_logger = get_logger(AllenIntervalNetworkSolver)


class _ReducedAllenInterval(AllenInterval):
    """An AllenInterval that does not carry the default start<=end
    (Duration) internal constraint."""

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        return []


class _ReducedAllenIntervalNetworkSolver(AllenIntervalNetworkSolver):
    """Java's ``ReducedAllenIntervalNetworkSolver``, meant to create
    ``_ReducedAllenInterval``s instead of ``AllenInterval``s -- but the Java
    override that would wire this up (``createVariablesSub``) is commented
    out in the source, so (matching that exact, if seemingly unintended,
    behavior) this class creates plain AllenIntervals just like its parent;
    ``create_reduced_intervals`` is tracked only for structural parity."""

    def __init__(self, origin: int, horizon: int, max_activities: int) -> None:
        super().__init__(origin, horizon, max_activities)
        self.create_reduced_intervals = True


def clone(
    old_solver: AllenIntervalNetworkSolver,
    intervals: list[Variable] | None,
    constraints: list[Constraint] | None,
    new_size: int,
) -> AllenIntervalNetworkSolver:
    """Clone an AllenIntervalNetworkSolver by copying its high-level
    AllenIntervalConstraints. ``intervals``/``constraints`` (if given) are
    updated in place with the corresponding new-solver references."""
    apsp_solver = cast(APSPSolver, old_solver.constraint_solvers[0])
    new_o = apsp_solver.o
    new_h = apsp_solver.h
    new_max_activities = len(old_solver.get_variables()) if new_size == 0 else new_size
    new_solver = AllenIntervalNetworkSolver(new_o, new_h, new_max_activities)

    old_variables = old_solver.get_variables()
    translate_intervals: dict[AllenInterval, AllenInterval] = {}
    for variable in old_variables:
        old_allen_interval = cast(AllenInterval, variable)
        new_allen_interval = cast(AllenInterval, new_solver.create_variable())
        new_allen_interval.marking = old_allen_interval.marking
        translate_intervals[old_allen_interval] = new_allen_interval

    old_constraints = old_solver.get_constraints()
    translate_constraints: dict[Constraint, Constraint] = {}
    for constraint in old_constraints:
        old_constraint = cast(AllenIntervalConstraint, constraint)
        old_from = cast(AllenInterval, old_constraint.from_)
        old_to = cast(AllenInterval, old_constraint.to)
        new_from = translate_intervals[old_from]
        new_to = translate_intervals[old_to]

        old_type = old_constraint.types[0]
        old_bounds = old_constraint.bounds

        new_constraint = AllenIntervalConstraint(old_type, *old_bounds)
        new_constraint.from_ = new_from
        new_constraint.to = new_to

        if not new_solver.add_constraint(new_constraint):
            raise RuntimeError(
                f"Could not add a constraint new constraint for {old_constraint} when cloning"
            )

        translate_constraints[old_constraint] = new_constraint

    if not old_constraints:
        _logger.warning("No constraints cloned()")

    if intervals is not None:
        for i, interval in enumerate(intervals):
            new_interval = translate_intervals.get(cast(AllenInterval, interval))
            if new_interval is None:
                raise RuntimeError(f"Failed to translate interval {interval}")
            intervals[i] = new_interval

    if constraints is not None:
        for i, con in enumerate(constraints):
            new_con = translate_constraints.get(con)
            if new_con is None:
                raise RuntimeError(f"Failed to translate constraint {con}")
            constraints[i] = new_con

    return new_solver


def create_reduced_copy(
    old_solver: AllenIntervalNetworkSolver,
    intervals_in_out: list[AllenInterval],
    additional_capacity: int = 0,
) -> AllenIntervalNetworkSolver:
    """A "reduced copy" of an AllenIntervalNetworkSolver: a subset of
    intervals from the original, temporally equivalent, but without the
    original's high-level constraints (replaced by lower-level
    SimpleDistanceConstraints). ``intervals_in_out`` is updated in place with
    the corresponding new-solver references."""
    old_apsp_solver = cast(APSPSolver, old_solver.constraint_solvers[0])
    new_o = old_apsp_solver.o
    new_h = old_apsp_solver.h
    new_solver = _ReducedAllenIntervalNetworkSolver(
        new_o, new_h, len(intervals_in_out) + additional_capacity
    )

    old_intervals = list(intervals_in_out)
    new_intervals: list[AllenInterval] = []
    for old_interval in old_intervals:
        new_interval = cast(AllenInterval, new_solver.create_variable())
        new_interval.marking = old_interval.marking
        new_intervals.append(new_interval)

    new_apsp_solver = cast(APSPSolver, new_solver.constraint_solvers[0])

    old_time_points: list[TimePoint] = [old_apsp_solver.source, old_apsp_solver.sink]
    new_time_points: list[TimePoint] = [new_apsp_solver.source, new_apsp_solver.sink]
    for old_interval, new_interval in zip(old_intervals, new_intervals):
        old_time_points.append(old_interval.start)
        old_time_points.append(old_interval.end)
        new_time_points.append(new_interval.start)
        new_time_points.append(new_interval.end)

    to_add: list[SimpleDistanceConstraint] = []
    for i in range(len(old_time_points)):
        for j in range(i):
            bounds = old_apsp_solver.get_distance_bounds(old_time_points[i], old_time_points[j])
            sdc = SimpleDistanceConstraint()
            sdc.from_ = new_time_points[i]
            sdc.to = new_time_points[j]
            sdc.minimum = bounds.min
            sdc.maximum = bounds.max
            # Must normalize: negative-minimum constraints cannot be added directly.
            sdc = sdc.normalize()
            to_add.append(sdc)

    if not new_apsp_solver.add_constraints(*to_add):
        raise RuntimeError("Failed to add SimpleDistanceConstraints to new solver")

    for old_interval, new_interval in zip(old_intervals, new_intervals):
        assert old_interval.est == new_interval.est
        assert old_interval.lst == new_interval.lst
        assert old_interval.eet == new_interval.eet
        assert old_interval.let == new_interval.let

    for i in range(len(old_time_points)):
        for j in range(len(old_time_points)):
            assert old_solver.get_admissible_distance_bounds(
                old_time_points[i], old_time_points[j]
            ) == new_solver.get_admissible_distance_bounds(new_time_points[i], new_time_points[j])

    intervals_in_out[:] = new_intervals

    new_solver.create_reduced_intervals = False

    return new_solver
