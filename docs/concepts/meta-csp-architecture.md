# Meta-CSP architecture

A **meta-CSP** is a CSP whose "variables" and "values" are themselves defined over one or more
lower-level ("ground") CSPs, rather than over a fixed, enumerable domain. A **meta-variable** is
a flaw or conflict detected in the ground CSP (e.g. two activities competing for the same
resource); a **meta-value** is a resolver — a set of ground-level constraints that, if posted,
removes that flaw. Solving the meta-CSP means backtracking search over meta-variables: pick the
highest-priority flaw, try its candidate resolvers in preference order, propagate the ground
CSP, and recurse; on failure, retract the resolver and try the next one (or backtrack further).
This generalizes classical CSP backtracking without requiring flaws or resolvers to be
enumerable in advance the way a domain is.

Before reaching meta-CSP level, metacsp has an intermediate layer: a **MultiVariable** is a
variable "implemented" by several lower-level variables (each possibly itself a MultiVariable),
together with the internal constraints relating them; a **MultiConstraint** is symmetrically a
constraint "implemented" by lower-level constraints. This lets composite concepts — an Allen
interval as two time points, an activity as an interval plus a symbolic value — be built up
from simpler solvers without duplicating their propagation logic.

## Realization in metacsp

`MultiVariable`/`MultiConstraint` are defined in `metacsp.framework.multi`, driven by
`MultiConstraintSolver`, which delegates variable/constraint creation to a list of internal
`ConstraintSolver`s (one entry in `ingredients` per internal solver, per instance). Adding a
`MultiConstraint` propagates its `internal_constraints` to the relevant internal solvers,
instantiating any "lifted" ground constraints along the way; retracting mirrors that
symmetrically.

`MetaConstraintSolver` (in `metacsp.framework.meta`) extends `MultiConstraintSolver` with
backtracking search itself: `backtrack()` repeatedly asks each registered `MetaConstraint` for
its highest-priority `get_meta_variable()`/`get_meta_values()`, posts a resolver via
`add_resolver`, and recurses, building a search tree (`DelegateTree` of `MetaVariable`s) as it
goes. `MetaConstraint` subclasses implement the domain-specific parts: what counts as a flaw
(`get_meta_variables`), what resolvers exist for it (`get_meta_values`), and how a resolved flaw
is marked (`mark_resolved_sub`). `FocusConstraint` optionally restricts search to a subset of
variables.

## API

- [`MultiVariable`](../api/framework.multi.md) / [`MultiConstraint`](../api/framework.multi.md)
  — variables/constraints "implemented" by lower-level ones.
- [`MultiConstraintSolver`](../api/framework.multi.md) — delegates to a list of internal
  ConstraintSolvers.
- [`MetaConstraint`](../api/framework.meta.md) — domain-specific flaw/resolver definitions.
- [`MetaVariable`](../api/framework.meta.md) — one search-tree node (a flaw plus the
  MetaConstraint that produced it).
- [`MetaConstraintSolver`](../api/framework.meta.md) — backtracking search over meta-variables,
  plus limited branch-and-bound support.

## See also

[Resource scheduling](../examples/resource-scheduling.md) — a MetaConstraintSolver resolving
resource conflicts end to end, the clearest concrete instance of this search loop.
