# Operator-based planning

[`examples/meta/test_simple_planner.py`](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/meta/test_simple_planner.py)
builds a small [`SimpleDomain`](../api/meta.simple_planner.md) in code (rather than parsing a
`.ddl` file) and runs [`SimplePlanner`](../api/meta.simple_planner.md) to justify two
unjustified `MoveTo()` goals.

```bash
python examples/meta/test_simple_planner.py
```

Components are tagged as actuators, and [`SimpleOperator`](../api/meta.simple_planner.md)s
describe how each can be achieved — a head activity, a required activity linked by an Allen
constraint, and (via `add_constraint`) extra unary constraints on the head:

```python
rd = SimpleDomain([6, 6, 6], ["power", "usbport", "serialport"], "TestDomain")
rd.add_actuator("Robot1")

operator1 = SimpleOperator(
    "Robot1::MoveTo()",
    [move_to_during_localization],
    ["LocalizationService::Localization()"],
    None,
)
operator1.add_constraint(duration_move_to, 0, 0)
rd.add_operator(operator1)
```

Other operators (`RFIDReader1::On()`, `LaserScanner1::On()`) have no requirements but consume
resource units — the fourth `SimpleOperator` argument. The domain and its resources are added as
`MetaConstraint`s of the planner, then two goal activities are created and marked
`UNJUSTIFIED`:

```python
planner.add_meta_constraint(rd)
for sch in rd.get_scheduling_meta_constraints():
    planner.add_meta_constraint(sch)

one = ground_solver.create_variable("Robot1")
one.set_symbolic_domain("MoveTo()")
one.marking = SimpleDomain.markings.UNJUSTIFIED

solved = planner.backtrack()
```

`backtrack()` repeatedly expands each unjustified activity via a matching operator (or unifies
it with an already-justified one), recursing into that operator's own requirements —
`LocalizationService::Localization()` needs either an RFID reader or a laser scanner on, each of
which consumes resource units checked by the registered `Scheduler` `MetaConstraint`s along the
way. See [Scheduling and planning](../concepts/scheduling-and-planning.md) for how expansion and
scheduling interleave.

See also: [Meta-CSP architecture](../concepts/meta-csp-architecture.md).
