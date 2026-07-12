# Scheduling and planning

Both **resource scheduling** and **task planning** are, in metacsp, meta-CSPs (see
[Meta-CSP architecture](meta-csp-architecture.md)) whose ground CSP is an activity network (see
[Activities and timelines](activities-and-timelines.md)): resolving flaws means posting temporal
precedence constraints between activities.

For scheduling, a flaw is a **resource conflict**: a "peak" — a set of temporally-overlapping
activities that together over-use a shared resource, e.g. a reusable resource of finite
capacity, or a state variable whose activities must not overlap unless they share an allowed
state. Peaks can be found exhaustively, by sampling, or pairwise; each is resolved by choosing a
**minimal critical set (MCS)** — the smallest set of activities within the peak such that
sequencing just one pair of them (via a precedence constraint) breaks the conflict — and the
ESTA heuristic orders candidate MCSs by how much temporal flexibility each choice preserves.

For planning, a flaw is an **unjustified activity**: one whose presence is not yet explained.
It is resolved either by *unification* with an already-justified activity of the same value, or
by *expansion* via a matching operator — a STRIPS-like rule pairing a head activity with a set
of requirement activities (each optionally tagged as a required precondition or an achieved
effect) and the temporal/resource constraints among them. Both mechanisms are meta-values for
the same flaw, so planning and scheduling naturally interleave: expanding an operator can
introduce new resource usages, and justifying an activity can resolve a scheduling conflict.

## Realization in metacsp

`Schedulable` is the common base for resource `MetaConstraint`s: it implements peak collection
(`get_meta_variables`, three strategies via `PEAKCOLLECTION`) and the ESTA-ordered resolver
search (`get_meta_values`, backed by `get_ordered_mcss`/`MCSData`); subclasses only implement
`is_conflicting`. `ReusableResource` and `StateVariable` are the two built-in resource types;
`StateVariableScheduler`/`Scheduler` are thin `MetaConstraintSolver`s wiring one of them up over
an `ActivityNetworkSolver`.

`SimpleDomain` is the planning `MetaConstraint`: `SimpleOperator`/`PlanningOperator` describe
operators (parsed from a `.ddl` domain-description file by `SimpleDomain.parse_domain`),
`expand_operator` instantiates one against a flaw, and `get_meta_values` chooses between
unification and expansion depending on whether the flawed component is a sensor, actuator, or
context variable. `SimplePlanner` is the `MetaConstraintSolver` driving it, turning accepted
resolvers' `VariablePrototype`s into real ground activities. `SimpleReusableResource` lets a
`SimpleDomain` additionally track resource usage per operator.

`SimpleHybridPlanner` (`metacsp.meta.hybrid_planner`) extends this same causal-planning loop
with a spatial dimension: its ground CSP additionally reasons about `SpatialFluent`s (movable
regions), and its `MetaConstraint`s check that a fluent's current placement doesn't drift from
what an operator committed to, or overlap another movable fluent — see
[Spatial reasoning](spatial-reasoning.md) for the spatial layer itself.

## API

- [`Schedulable`](../api/meta.symbols_and_time.md) / [`ReusableResource`](../api/meta.symbols_and_time.md) /
  [`StateVariable`](../api/meta.symbols_and_time.md) /
  [`StateVariableScheduler`](../api/meta.symbols_and_time.md) /
  [`Scheduler`](../api/meta.symbols_and_time.md) — resource conflict scheduling.
- [`SimpleDomain`](../api/meta.simple_planner.md) / [`SimpleOperator`](../api/meta.simple_planner.md) /
  [`SimplePlanner`](../api/meta.simple_planner.md) /
  [`PlanningOperator`](../api/meta.simple_planner.md) — operator-based planning.
- [`SimpleHybridPlanner`](../api/meta.hybrid_planner.md) — causal planning extended with
  spatial-placement checks.

## See also

[Resource scheduling](../examples/resource-scheduling.md) and
[Planning](../examples/planning.md).
