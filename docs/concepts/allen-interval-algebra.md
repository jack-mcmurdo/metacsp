# Allen interval algebra

Allen's interval algebra describes how two time intervals can relate to one another
qualitatively: there are exactly 13 mutually exclusive **basic relations** — `Before`/`After`,
`Meets`/`MetBy`, `Overlaps`/`OverlappedBy`, `Starts`/`StartedBy`, `During`/`Contains`,
`Finishes`/`FinishedBy`, and `Equals`. A constraint between two intervals can be a *disjunction*
of several basic relations ("A is `Before` or `Meets` B"); solving a network of such disjunctive
constraints uses **path consistency**: for every triple of intervals, restrict the relation
between the first and third to what its composition through the second could produce, and
repeat until a fixed point (or a relation empties out, meaning inconsistency).

Basic relations also have a *quantitative* reading: each corresponds to bounds on the
`[start, end]` distances between the two intervals' endpoints, so a (possibly disjunctive, but
tractable/convex) Allen constraint can alternatively be compiled straight down to STP distance
constraints on the endpoints (see [Temporal reasoning](temporal-reasoning.md)) — no separate
qualitative solver needed. A **fuzzy** variant additionally attaches a possibility degree (in
`[0, 1]`) to each basic relation in a disjunction, for representing graded belief.

## Realization in metacsp

For the purely qualitative case, `SimpleAllenInterval` is a `Variable` (not built from time
points) whose domain is a `SimpleInterval`; `QualitativeAllenIntervalConstraint` carries a set
of `Type` values as its disjunction, and `QualitativeAllenSolver` runs path consistency directly
over those relation sets, using a precomputed `TRANSITION_TABLE` for composition.

For the quantitative case — the one most of the codebase builds on — `AllenInterval` is a
`MultiVariable` over two `TimePoint`s (start, end); `AllenIntervalConstraint` compiles its
`Type`(s) to `SimpleDistanceConstraint`s between those points (see
`create_internal_constraints_from_to`), so propagation is entirely STP propagation.
`AllenIntervalNetworkSolver` composes a single internal `APSPSolver` for this purpose.

The fuzzy variant lives in `metacsp.fuzzy_allen_interval`: `FuzzyAllenIntervalConstraint` pairs
each `Type` with a possibility degree, and `FuzzyAllenIntervalNetworkSolver` runs a fuzzified
path-consistency algorithm over `SimpleAllenInterval`-style variables.

## API

- [`QualitativeAllenIntervalConstraint`](../api/time.qualitative.md) /
  [`QualitativeAllenSolver`](../api/time.qualitative.md) /
  [`SimpleAllenInterval`](../api/time.qualitative.md) — purely qualitative path consistency.
- [`AllenInterval`](../api/multi.allen_interval.md) /
  [`AllenIntervalConstraint`](../api/multi.allen_interval.md) /
  [`AllenIntervalNetworkSolver`](../api/multi.allen_interval.md) — quantitative Allen
  constraints compiled to STP bounds.
- [`FuzzyAllenIntervalConstraint`](../api/fuzzy_allen_interval.md) /
  [`FuzzyAllenIntervalNetworkSolver`](../api/fuzzy_allen_interval.md) — possibility-degree
  disjunctions and fuzzy path consistency.

## See also

[Activities and Allen constraints](../examples/activities.md) — Allen constraints used to
temporally order activities on a timeline.
