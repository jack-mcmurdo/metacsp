# STP bounds propagation

[`examples/test_apsp_solver.py`](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/test_apsp_solver.py)
walks through [`APSPSolver`](../api/time.md) propagation as constraints are added and removed,
watching the network's rigidity change.

```bash
python examples/test_apsp_solver.py
```

Three time points are related by [`SimpleDistanceConstraint`](../api/time.md)s to the solver's
implicit origin/horizon time points and to each other:

```python
solver = APSPSolver(100, 500)
one, two, three = solver.create_variables(3)

con1 = SimpleDistanceConstraint()
con1.from_ = solver.get_variable(0)
con1.to = one
con1.minimum = 60
con1.maximum = 75
```

`add_constraints` posts several constraints in one batch (accepted or rejected together);
`add_constraint` posts one at a time. Once posted, [`get_rms_rigidity`](../api/time.md) reports
how flexible the network still is — 1.0 for a fully rigid (all bounds collapsed to a point)
network, 0.0 for an unconstrained one:

```python
for _ in range(3):
    solver.add_constraint(con5)
    print("Rigidity:", solver.get_rms_rigidity())

    solver.remove_constraint(con2)
    print("Rigidity:", solver.get_rms_rigidity())
```

Removing and re-adding constraints in a loop like this is a compact way to see propagation react
in both directions — rigidity rises when a tightening constraint goes in, and falls again when a
loosening one is removed or a tightening one is retracted.

See also: [Temporal reasoning](../concepts/temporal-reasoning.md),
[Constraint networks](../concepts/constraint-networks.md).
