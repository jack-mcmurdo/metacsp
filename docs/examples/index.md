# Examples

Every example is a plain, standalone Python script — run one directly from the repo root:

```bash
python examples/test_apsp_solver.py
```

## Directory map

- `examples/*.py` — top-level, single-solver demos (STP, Boolean SAT, Allen interval, RCC,
  geometry, DE9IM, ...).
- `examples/multi/` — `multi.*` layer demos (activities, allen interval network solver,
  rectangle/block algebra, ...).
- `examples/meta/` — `meta.*` layer demos (resource scheduling, planning, trajectory envelope
  scheduling, context inference, ...).
- `examples/tutorial/` — end-to-end scenarios ported from the separate
  [meta-csp-tutorial](https://github.com/FedericoPecora/meta-csp-tutorial) repo: trajectory
  envelope coordination (`coordination/`), dispatching (`dispatching/`), and proactive planning
  (`planning/`), exercising the library the way a robot integration would. Some are interactive.

[examples/SKIPPED.md](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/SKIPPED.md)
lists the handful of upstream Java examples that could not be meaningfully ported (Swing-only,
dead upstream code, or missing fixtures), each with a one-line reason.

The six walkthroughs below annotate specific examples in more depth; every other script in
`examples/` is runnable the same way and generally shorter/more self-contained.
