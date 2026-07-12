"""Tests for meta/spatioTemporal/paths: Map and TrajectoryEnvelopeScheduler
(M17).

There is no ported JUnit test class for these (``tests/`` in the Java source
has no ``TestTrajectoryEnvelopeScheduler*.java``); PLAN.md's explicit
acceptance criterion for M17 is "the scheduler example completes with a
consistent network", so these tests build a fixture scenario (reusing the
``path1.path``/``path3.path`` trajectory fixtures copied into
``tests/data/paths/`` for M14) and assert *structural* consistency
properties -- backtracking succeeds and no spatial+temporal conflict
remains afterwards -- rather than inventing specific numeric bounds as if
from a Java oracle, per PLAN.md's "search-order divergence" risk note.
"""

from __future__ import annotations

from pathlib import Path

from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.meta.spatio_temporal.paths.trajectory_envelope_scheduler import _DependencyEdge
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope
from metacsp.utility.graph import DirectedSparseMultigraph

_DATA_DIR = Path(__file__).resolve().parent / "data" / "paths"


def _build_two_robot_scheduler() -> (
    tuple[TrajectoryEnvelopeScheduler, TrajectoryEnvelope, TrajectoryEnvelope, Map]
):
    meta_solver = TrajectoryEnvelopeScheduler(0, 100_000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(2)
    assert vars_ is not None
    var0, var1 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)

    var0.set_footprint(1.3, 3.5, 0.0, 0.0)
    var0.trajectory = Trajectory(str(_DATA_DIR / "path1.path"))
    var1.set_footprint(1.3, 3.5, 0.0, 0.0)
    var1.trajectory = Trajectory(str(_DATA_DIR / "path3.path"))

    var0.robot_id = 1
    var1.robot_id = 2

    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)
    return meta_solver, var0, var1, map_


def test_map_is_conflicting_requires_different_robots_and_spatial_overlap() -> None:
    meta_solver, var0, var1, map_ = _build_two_robot_scheduler()

    # Same robot: never conflicting, regardless of geometry.
    var0.robot_id = 5
    var1.robot_id = 5
    assert map_.is_conflicting([var0, var1]) is False

    # Different robots, and (per the fixture paths) their un-refined
    # reference envelopes do spatially overlap.
    var0.robot_id = 1
    var1.robot_id = 2
    assert var0.envelope_variable.domain.geometry.intersects(var1.envelope_variable.domain.geometry)
    assert map_.is_conflicting([var0, var1]) is True

    # A single-activity peak is never conflicting.
    assert map_.is_conflicting([var0]) is False


def test_refine_trajectory_envelopes_splits_overlapping_pair() -> None:
    meta_solver, var0, var1, _map = _build_two_robot_scheduler()
    solver = meta_solver.constraint_solvers[0]
    before_count = len(solver.get_variables())

    refined = meta_solver.refine_trajectory_envelopes()

    after_count = len(solver.get_variables())
    # Refinement created new sub-envelope variables.
    assert after_count > before_count
    assert len(refined.get_variables()) > 0
    # At least one of the two original envelopes was split.
    assert var0.has_sub_envelopes or var1.has_sub_envelopes

    # A second refinement pass over the (now smaller, non-overlapping)
    # pieces should not find anything left to split.
    refined_again = meta_solver.refine_trajectory_envelopes()
    assert refined_again.get_variables() == []


def test_scheduler_backtrack_yields_consistent_conflict_free_network() -> None:
    meta_solver, var0, var1, map_ = _build_two_robot_scheduler()

    meta_solver.refine_trajectory_envelopes()
    solved = meta_solver.backtrack()
    assert solved is True

    # No spatial+temporal conflict remains: the Map MetaConstraint's peak
    # collection over the ground envelopes it is tracking usage of finds no
    # conflicting peak.
    assert map_.get_meta_variables() == []

    # Every pairwise-conflicting ground envelope pair (different robots,
    # overlapping footprints) must now be temporally disjoint.
    solver = meta_solver.constraint_solvers[0]
    leaves = [v for v in solver.get_variables() if not v.has_sub_envelopes]
    for i in range(len(leaves)):
        for j in range(i + 1, len(leaves)):
            a, b = leaves[i], leaves[j]
            if a.robot_id == b.robot_id:
                continue
            geom_a = a.envelope_variable.domain.geometry
            geom_b = b.envelope_variable.domain.geometry
            if not geom_a.intersects(geom_b):
                continue
            ta, tb = a.temporal_variable, b.temporal_variable
            assert ta.eet <= tb.est or tb.eet <= ta.est

    # At least one resolver (a BeforeOrMeets precedence constraint) was
    # actually added to arbitrate the original spatial conflict.
    assert len(meta_solver.get_added_resolvers()) >= 1


def test_get_current_dependencies_reflects_added_before_or_meets_constraints() -> None:
    meta_solver, var0, var1, map_ = _build_two_robot_scheduler()
    meta_solver.refine_trajectory_envelopes()
    solved = meta_solver.backtrack()
    assert solved is True

    dep_graph = meta_solver.get_current_dependencies()
    assert isinstance(dep_graph, DirectedSparseMultigraph)

    ground_solver_cn = meta_solver.constraint_solvers[0].constraint_network
    before_or_meets = [
        c
        for c in ground_solver_cn.get_constraints()
        if isinstance(c, AllenIntervalConstraint)
        and c.types[0] is AllenIntervalConstraint.Type.BeforeOrMeets
    ]
    if before_or_meets:
        assert dep_graph.edge_count >= 1
        for edge in dep_graph.edges():
            assert isinstance(edge, _DependencyEdge)
    else:
        assert dep_graph.edge_count == 0


def test_scheduler_constructor_collapses_animation_time_and_max_trajectories() -> None:
    default_scheduler = TrajectoryEnvelopeScheduler(0, 1000)
    assert default_scheduler.animation_time == 0

    animated_scheduler = TrajectoryEnvelopeScheduler(0, 1000, 5)
    assert animated_scheduler.animation_time == 5

    capped_scheduler = TrajectoryEnvelopeScheduler(0, 1000, max_trajectories=3)
    assert capped_scheduler.animation_time == 0
    vars_ = capped_scheduler.constraint_solvers[0].create_variables(3)
    assert vars_ is not None and len(vars_) == 3
