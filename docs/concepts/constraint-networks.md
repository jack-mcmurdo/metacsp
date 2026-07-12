# Constraint networks

A Constraint Satisfaction Problem (CSP) is a set of **variables**, each with a **domain** of
possible values, and a set of **constraints** restricting which combinations of values are
jointly allowed. Solving a CSP means finding an assignment of one value per variable that
satisfies every constraint; a CSP is **consistent** if no constraint can be shown to rule out
every remaining value of some variable (a weaker, checkable property than full solvability).
Binary constraints — over exactly two variables — are the common case and are usually
represented as edges of a constraint graph, which is what metacsp does directly.

## Realization in metacsp

`Variable` and `Constraint` are abstract base classes; concrete solvers (STP, Allen interval,
Boolean SAT, ...) define their own subclasses. A `Domain` belongs to exactly one `Variable` and
supports pluggable `ValueChoiceFunction`s for picking a concrete value out of a (possibly
still-flexible) domain.

`ConstraintNetwork` is the graph holding a solver's variables and constraints: binary
constraints become a single edge between two variables; n-ary constraints become a hub
"hyperedge" (a `DummyVariable` connected to every variable in the constraint's scope by a
`DummyConstraint`). Every add/remove of a variable or constraint fires a change-listener
callback (register one with `add_change_listener`), which is what `metacsp.serialization`'s
`SnapshotPublisher` and `metacsp.viz` build on to observe a solver live.

`ConstraintSolver` is the common driver: it owns one `ConstraintNetwork`, exposes
`create_variables`/`add_constraint(s)`/`remove_constraint(s)`, and defines the propagation
contract subclasses implement via `propagate()`. Auto- vs. manual-propagation is controlled by
`ConstraintSolver.Options`; concrete solvers such as `APSPSolver` (see
[Temporal reasoning](temporal-reasoning.md)) instead propagate incrementally inside their own
`add_constraints_sub` hook.

## API

- [`Variable`](../api/framework.md) — a CSP variable; equality is by id + class.
- [`Domain`](../api/framework.md) — a variable's set of possible values, with
  `ValueChoiceFunction` support.
- [`Constraint`](../api/framework.md) / [`BinaryConstraint`](../api/framework.md) — n-ary and
  two-variable constraints, compared by identity.
- [`ConstraintNetwork`](../api/framework.md) — the graph of variables and constraints, with
  change-listener notifications.
- [`ConstraintSolver`](../api/framework.md) — the base driver contract (create/add/remove,
  `propagate()`).

## See also

[STP quickstart](../examples/stp.md) — the smallest concrete instance of this contract:
one `ConstraintSolver` subclass, its `Variable`s, and one `Constraint`.
