# Getting Started

## Install

From a clone of the repo:

```bash
pip install -e ".[dev]"      # development: tests, formatter, dearpygui
```

`dev` pulls in `dearpygui` for the optional live viewer ([metacsp.viz](api/viz.md)); to install
just that extra on its own, use `pip install -e ".[viz]"`.

## First solver

metacsp's most basic building block is the [APSPSolver](api/time.md), a Simple Temporal
Problem (STP) solver: variables are time points, constraints bound the distance between two
time points, and the solver propagates those bounds with all-pairs shortest paths.

```python
from metacsp.time import APSPSolver, SimpleDistanceConstraint

# A network with horizon [0, 1000]: all time points fall in this range.
solver = APSPSolver(0, 1000)

# Create two TimePoint variables.
a, b = solver.create_variables(2)

# a must occur at least 10, and at most 20, time units before b.
con = SimpleDistanceConstraint()
con.from_ = a
con.to = b
con.minimum = 10
con.maximum = 20

consistent = solver.add_constraint(con)
print("Consistent?", consistent)

# After propagation, each TimePoint's Domain (an Interval) carries its
# earliest/latest bounds.
print("a bounds:", a.domain.bounds)
print("b bounds:", b.domain.bounds)
```

`add_constraint` returns `True`; `APSPSolver` propagates each constraint incrementally as it is
added (regardless of the general [ConstraintSolver.Options](api/framework.md) auto-propagation
setting), so `a`/`b`'s [TimePoint](api/time.md) bounds are already updated to reflect the new
constraint.

## Running examples

Runnable demos live in `examples/` — plain, standalone Python scripts:

```bash
python examples/test_apsp_solver.py
```

- `examples/multi/`, `examples/meta/` mirror the module layout for those solver layers.
- `examples/tutorial/` ports the demos of the separate
  [meta-csp-tutorial](https://github.com/FedericoPecora/meta-csp-tutorial) repo — end-to-end
  trajectory-envelope coordination, dispatching, and proactive-planning scenarios that exercise
  the library the way a robot integration would. Some are interactive, e.g.
  `python examples/tutorial/dispatching/simple_dispatching_example.py`.
- [examples/SKIPPED.md](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/SKIPPED.md)
  lists the handful of upstream Java examples that could not be meaningfully ported (Swing-only,
  dead upstream code, or missing fixtures), each with a one-line reason.

## Logging

Every metacsp class logs to its own `logging.getLogger("metacsp.<ClassName>")`, all children of
the `"metacsp"` logger. Turn on debug output for the whole library with
[metacsp.utility.logging.set_level](api/utility.md):

```python
import logging
from metacsp.utility.logging import set_level

set_level(logging.DEBUG)
```
