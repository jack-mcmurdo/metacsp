# Spatial reasoning

Qualitative spatial calculi describe how regions relate without needing exact coordinates, the
spatial analogue of Allen's interval algebra. **RCC (Region Connection Calculus)** classifies
two regions' relationship — disconnected, touching, overlapping, one inside the other, equal —
purely from topology. **Cardinal direction** constraints instead state relative position: North,
South-East, and so on. **DE9IM** (Dimensionally Extended 9-Intersection Model) is the general
mechanism both can be built from: a 3×3 matrix, one cell per (interior/boundary/exterior) ×
(interior/boundary/exterior) pair, recording the dimension of each pairwise intersection between
two geometries — RCC and cardinal-direction relations are each expressible as a specific pattern
over that matrix.

**Rectangle** and **block algebra** lift Allen's interval algebra to two (rectangle) or three
(block/cuboid) axes at once: a rectangle constraint is a pair of interval constraints, one per
axis, so path consistency and STP-style propagation carry over directly. Underneath all of this
sits a metric geometry layer — polygons, points, collision/impulse math — used both for concrete
shape reasoning and, via `TrajectoryEnvelope` (see
[Trajectory envelopes](trajectory-envelopes.md)), physical robot footprints.

## Realization in metacsp

`DE9IMRelation` is the general spatial constraint type, checked by `DE9IMRelationSolver` against
`GeometricShapeVariable`s (`PointDomain`/`LineStringDomain`/`PolygonalDomain`, wrapping Shapely
geometries — GEOS itself being the C++ port of the JTS library the Java original used).
`RCCConstraint`/`RCCConstraintSolver` implement RCC-8 path consistency directly;
`CardinalConstraint` states a cardinal direction between two `Rectangle`-domain `Region`s.

`RectangleConstraintSolver`/`RectangleConstraint` compose two `AllenIntervalNetworkSolver`s (one
per axis) under a `RectangularRegion` `MultiVariable`; `BlockConstraintSolver`/
`BlockAlgebraConstraint` do the same over three axes with `RectangularCuboidRegion`. Both have a
`Unary*Constraint` variant pinning one region absolutely rather than relative to another.
`GeometricConstraintSolver` (`metacsp.spatial.geometry`) is the lower-level physics layer:
`Polygon` variables, collision detection (`CollisionPolygonPolygon`), and impulse-based
resolution — used to check DC/INSIDE `GeometricConstraint`s directly on polygon geometry rather
than through Shapely.

## API

- [`DE9IMRelation`](../api/multi.spatial.de9im.md) /
  [`DE9IMRelationSolver`](../api/multi.spatial.de9im.md) — the general DE9IM spatial-relation
  solver.
- [`RCCConstraint`](../api/spatial.rcc.md) / [`RCCConstraintSolver`](../api/spatial.rcc.md) —
  RCC-8 path consistency.
- [`CardinalConstraint`](../api/spatial.cardinal.md) — relative cardinal direction.
- [`RectangleConstraintSolver`](../api/multi.spatial.rectangle_algebra.md) /
  [`UnaryRectangleConstraint`](../api/multi.spatial.rectangle_algebra.md) — 2-axis rectangle
  algebra.
- [`BlockConstraintSolver`](../api/multi.spatial.block_algebra.md) — 3-axis (cuboid) block
  algebra.
- [`GeometricConstraintSolver`](../api/spatial.geometry.md) — polygon collision/physics layer.

## See also

[Trajectory envelopes](../examples/trajectory-envelopes.md) — spatial reasoning applied to
robot footprints swept along paths.
