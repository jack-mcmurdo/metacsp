# Trajectory envelopes

A **trajectory envelope** represents a robot's committed path together with the *spatial
footprint it sweeps* while following it: given a path (a sequence of poses) and a footprint
polygon (the robot's outline), sweeping the footprint along the path and taking the union
produces a single polygon — the envelope — covering everywhere the robot's body could be while
executing that path. Envelopes are additionally sliced into consecutive **ground envelopes**
along the path, each with its own STP-bounded transit time (see
[Temporal reasoning](temporal-reasoning.md)), so "where is the robot at time *t*" and "how much
of the swept area is occupied by time *t*" are both answerable per-segment rather than only for
the whole path.

Scheduling multiple robots' envelopes is then a spatio-temporal instance of the meta-CSP pattern
(see [Meta-CSP architecture](meta-csp-architecture.md)): two envelopes belonging to different
robots **conflict** if their swept polygons intersect *and* their temporal placements overlap.
Refining an overlapping pair into smaller ground envelopes shrinks the intersecting region
(and, correspondingly, the time window that matters) until a conflict can be resolved with a
precedence constraint — one robot's ground envelope must finish before the other's may start —
without over-constraining the parts of each path that never actually overlap.

## Realization in metacsp

`Pose`/`PoseSteering` describe a 2D (or 3D) robot pose plus steering angle; `Trajectory` is a
path of `PoseSteering`s with a temporal profile (`dts`, minimum transition times between
consecutive poses). `TrajectoryEnvelope` is a `MultiVariable` combining a `SymbolicVariableActivity`
(temporal + symbolic part — see [Activities and timelines](activities-and-timelines.md)), a
reference-path `GeometricShapeVariable`, and spatial/inner-envelope `GeometricShapeVariable`s;
setting its `trajectory` sweeps the footprint (`make_footprint`) along the path and posts the
resulting geometry, plus a minimum-duration `AllenIntervalConstraint`.
`TrajectoryEnvelopeSolver` composes an `ActivityNetworkSolver` and a `DE9IMRelationSolver` to
drive both parts.

`meta.spatio_temporal.paths.Map` is the `MetaConstraint` detecting spatio-temporal conflicts
between different robots' envelopes (using `Schedulable`'s peak machinery — see
[Scheduling and planning](scheduling-and-planning.md)); `TrajectoryEnvelopeScheduler` is the
`MetaConstraintSolver` driving it, and additionally implements envelope **refinement**
(`refine_trajectory_envelopes`) — splitting an envelope into sub-envelopes along the region
where it overlaps a conflicting one.

## API

- [`Pose`](../api/multi.spatio_temporal.paths.md) / [`PoseSteering`](../api/multi.spatio_temporal.paths.md) /
  [`Trajectory`](../api/multi.spatio_temporal.paths.md) — path representation.
- [`TrajectoryEnvelope`](../api/multi.spatio_temporal.paths.md) /
  [`TrajectoryEnvelopeSolver`](../api/multi.spatio_temporal.paths.md) — the swept-footprint
  MultiVariable and its solver.
- [`Map`](../api/meta.spatio_temporal.paths.md) /
  [`TrajectoryEnvelopeScheduler`](../api/meta.spatio_temporal.paths.md) — conflict detection and
  resolution across robots.

## See also

[Trajectory envelope scheduling](../examples/trajectory-envelopes.md) — envelope construction
and multi-robot conflict resolution end to end.
