# Activities, Allen constraints, and timelines

[`examples/multi/test_activity_network_solver.py`](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/multi/test_activity_network_solver.py)
builds two activities, links their symbolic values and temporal placements, and posts the
result to an [`ActivityNetworkSolver`](../api/multi.activity.md) in one batch.

```bash
python examples/multi/test_activity_network_solver.py
```

An `ActivityNetworkSolver` is created with a fixed symbol vocabulary, and two
[`SymbolicVariableActivity`](../api/multi.activity.md) variables are restricted to subsets of it:

```python
solver = ActivityNetworkSolver(0, 500, ["A", "B", "C", "D", "E", "F"])
act1 = solver.create_variable()
act1.set_symbolic_domain("A", "B", "C")
act2 = solver.create_variable()
act2.set_symbolic_domain("B", "C", "D")
```

[`SymbolicValueConstraint`](../api/multi.symbols.md) relates the two activities' symbolic
values (here, `EQUALS` — they must end up with the same symbol — and a unary `VALUESUBSET`
further narrowing `act1`); [`AllenIntervalConstraint`](../api/multi.allen_interval.md) relates
their temporal placement (`Before`, plus `Duration`/`Release` unary constraints):

```python
con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
con1.set_from(act1)
con1.set_to(act2)

con2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Before, Bounds(10, 20))
con2.from_ = act1
con2.to = act2

print(solver.add_constraints(con1, con1a, con2, con3, con4, con5, con5a))
```

Both constraint types are posted together, since `EQUALS`/`VALUESUBSET` and `Before` interact:
narrowing the symbolic overlap and fixing a `[10, 20]` gap between the activities must be
jointly consistent for `add_constraints` to succeed.

Once solved, [`SymbolicTimeline`](../api/meta.symbols_and_time.md) reads a component's
activities back out as pulses plus the symbol(s) held between them — see
[Activities and timelines](../concepts/activities-and-timelines.md) for how that projection
works, and [`metacsp.serialization.timeline_to_dict`](../api/serialization.md) for its JSON
form.

See also: [Allen interval algebra](../concepts/allen-interval-algebra.md).
