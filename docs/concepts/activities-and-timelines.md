# Activities and timelines

An **activity** pairs a flexible *temporal placement* (an Allen interval — see
[Allen interval algebra](allen-interval-algebra.md)) with a *symbolic value*: what is true, or
what is happening, during that interval. Constraining activities' symbolic values needs its own
machinery: a **symbolic variable** ranges over a fixed vocabulary of symbols and can hold one or
several of them at once (a set-valued domain), with constraints expressing equality, difference,
containment, or a fixed unary value between two such variables. Under the hood this is a
Boolean satisfiability problem — one Boolean variable per vocabulary symbol — so symbolic
constraints compile down to a conjunctive normal form (CNF) formula and are solved by a SAT
solver.

A **timeline** reads a solved activity network back out as a step function over time: a sorted
list of *pulses* (every time some activity starts or ends on a given component) and, for each
interval between consecutive pulses, the symbol(s) held by whatever activity is active there
(or "undetermined"/"inconsistent" if none is, or a domain wipeout occurred). This is the natural
way to inspect what a component of a system is doing throughout a schedule, and is what
`metacsp.viz`'s live Gantt view and `metacsp.serialization`'s JSON export both build on.

## Realization in metacsp

`SymbolicVariable` is a `MultiVariable` over one `BooleanVariable` per solver-wide vocabulary
symbol (see `SymbolicVariableConstraintSolver`, which owns that vocabulary and an internal
`BooleanSatisfiabilitySolver`); `SymbolicValueConstraint` compiles its `Type` (`EQUALS`,
`DIFFERENT`, `VALUESUBSET`, ...) to CNF over those Boolean variables via
`BooleanConstraint.create_boolean_constraints`.

`SymbolicVariableActivity` is the activity itself: a `MultiVariable` pairing an `AllenInterval`
(internal variable 0) with a `SymbolicVariable` (internal variable 1), with no constraints
between them — `ActivityNetworkSolver` composes an `AllenIntervalNetworkSolver` and a
`SymbolicVariableConstraintSolver` to drive both parts together. `Timeline` computes pulses from
a component's activities' earliest start/end times; `SymbolicTimeline` is the concrete
implementation returning the union of symbols held in each pulse interval — this is what
`metacsp.serialization.timeline_to_dict` and the live viewer both read.

## API

- [`SymbolicVariable`](../api/multi.symbols.md) /
  [`SymbolicVariableConstraintSolver`](../api/multi.symbols.md) — set-valued symbolic variables
  over a shared vocabulary.
- [`BooleanVariable`](../api/boolean_sat.md) /
  [`BooleanSatisfiabilitySolver`](../api/boolean_sat.md) — the underlying SAT layer.
- [`SymbolicVariableActivity`](../api/multi.activity.md) /
  [`ActivityNetworkSolver`](../api/multi.activity.md) /
  [`Timeline`](../api/multi.activity.md) — activities and their timeline projection.
- [`SymbolicTimeline`](../api/meta.symbols_and_time.md) — the concrete Timeline used by
  scheduling/planning MetaConstraintSolvers.

## See also

[Activities and Allen constraints](../examples/activities.md) — building an activity network,
posting Allen constraints, and extracting a timeline.
