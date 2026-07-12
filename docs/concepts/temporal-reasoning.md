# Temporal reasoning

A **Simple Temporal Problem (STP)** represents time points and binary distance constraints
between them: for time points *x* and *y*, a constraint bounds *y - x* to `[min, max]`. Every
STP maps directly onto a **distance graph**, with one directed, weighted edge per bound; the STP
is consistent iff that graph has no negative cycle. Propagating an STP means computing, for
every pair of time points, the tightest possible distance bounds consistent with all posted
constraints — equivalently, the all-pairs shortest paths of the distance graph, computable with
Floyd–Warshall. Once propagated, each time point's own earliest/latest possible values follow
from its distance to a fixed origin and horizon.

A **TCSP** (Temporal CSP) generalizes STP to *disjunctive* distance constraints — "x - y is in
`[1, 5]` or `[10, 20]`" — which is no longer solvable by shortest paths alone: committing to one
disjunct per constraint reduces a TCSP to an STP, so a TCSP is solved by meta-CSP search over
those commitments (see [Meta-CSP architecture](meta-csp-architecture.md)), backtracking on
inconsistency.

## Realization in metacsp

`APSPSolver` is the STP solver: time points are `TimePoint` variables, `SimpleDistanceConstraint`
posts one `[min, max]` bound, and the distance matrix is a single `numpy` array updated
incrementally per constraint (or recomputed from scratch after removals) rather than via the
generic `ConstraintSolver.propagate()` hook. `Bounds` is the general min/max pair type used
throughout the codebase, not just for time. `Interval` is the `Domain` of a `TimePoint`,
carrying its propagated `[earliest, latest]` bounds and exposing "ET"/"LT"
(earliest-time/latest-time) `ValueChoiceFunction`s.

For disjunctive constraints, `multi.tcsp.DistanceConstraint` is a `MultiConstraint` whose
`internal_constraints` are the STP constraints for its currently-committed disjunct (or none, if
uncommitted); `multi.tcsp.DistanceConstraintSolver` composes an `APSPSolver` under a
`MultiConstraintSolver`. `meta.tcsp.TCSPSolver` drives the meta-CSP search: its
`meta.tcsp.TCSPLabeling` `MetaConstraint` finds uncommitted `DistanceConstraint`s and offers one
meta-value per disjunct, backtracking via the base `MetaConstraintSolver` machinery.

## API

- [`APSPSolver`](../api/time.md) — Floyd–Warshall STP solver.
- [`TimePoint`](../api/time.md) / [`Bounds`](../api/time.md) /
  [`Interval`](../api/time.md) — the STP's variables, min/max pairs, and domain.
- [`SimpleDistanceConstraint`](../api/time.md) — one `[min, max]` distance bound.
- [`DistanceConstraintSolver`](../api/multi.tcsp.md) /
  [`MultiTimePoint`](../api/multi.tcsp.md) — disjunctive TCSP constraints over an internal STP.
- [`TCSPSolver`](../api/meta.tcsp.md) / [`TCSPLabeling`](../api/meta.tcsp.md) — meta-CSP search
  that commits each disjunctive constraint to one disjunct at a time.

## See also

[STP quickstart](../examples/stp.md) — bounds propagation on a small hand-built network.
