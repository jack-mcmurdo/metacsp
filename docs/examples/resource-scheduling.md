# Resource scheduling

[`examples/meta/test_reusable_resource_scheduler.py`](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/meta/test_reusable_resource_scheduler.py)
runs a [`Scheduler`](../api/meta.symbols_and_time.md) end to end: three activities compete for
two [`ReusableResource`](../api/meta.symbols_and_time.md)s, and meta-CSP backtracking finds a
set of precedence constraints resolving every conflict.

```bash
python examples/meta/test_reusable_resource_scheduler.py
```

Three activities are created on the ground `ActivityNetworkSolver` (reached via the
`Scheduler`'s `constraint_solvers[0]`), each with a `Duration` bound and one temporal ordering
between the first two:

```python
meta_solver = Scheduler(0, 600, 0)
ground_solver = meta_solver.constraint_solvers[0]

one = ground_solver.create_variable("comp1")
one.set_symbolic_domain("2")   # activity "one" uses 2 units of a resource
...
ground_solver.add_constraints(dur1, dur2, dur3, con1)
```

Each activity's symbolic value (`"2"`, `"1"`, `"3"`) is interpreted as its usage amount by
`ReusableResource.is_conflicting`. Two resources are registered as `MetaConstraint`s, each with
a different capacity and a different subset of activities using it:

```python
rr1 = ReusableResource(var_oh, val_oh, 4)
rr2 = ReusableResource(var_oh, val_oh, 3)
rr1.set_usage(one, two, three)
rr2.set_usage(two, three)
meta_solver.add_meta_constraint(rr1)
meta_solver.add_meta_constraint(rr2)

print("SOLVED?", meta_solver.backtrack())
```

`backtrack()` drives the full meta-CSP search described in
[Scheduling and planning](../concepts/scheduling-and-planning.md): both resources' peaks are
collected, each conflicting peak's minimal critical set is found, and a precedence constraint is
posted (and, on failure, retracted and retried) until every conflict is resolved or the search
is exhausted.

See also: [Meta-CSP architecture](../concepts/meta-csp-architecture.md).
