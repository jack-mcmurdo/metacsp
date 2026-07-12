# Trajectory envelope scheduling

[`examples/meta/test_trajectory_envelope_scheduler.py`](https://github.com/jack-mcmurdo/metacsp/blob/master/examples/meta/test_trajectory_envelope_scheduler.py)
builds two [`TrajectoryEnvelope`](../api/multi.spatio_temporal.paths.md)s from path files, then
uses [`TrajectoryEnvelopeScheduler`](../api/meta.spatio_temporal.paths.md) to refine and resolve
their spatial overlap. It reads fixture paths from `tests/data/paths/`.

```bash
python examples/meta/test_trajectory_envelope_scheduler.py
```

Two envelopes are created and given a footprint (`(width, length, dw, dl)` form) and a
[`Trajectory`](../api/multi.spatio_temporal.paths.md) loaded straight from a `.path` file:

```python
meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
var0, var1 = meta_solver.constraint_solvers[0].create_variables(2)

traj0 = Trajectory(str(_DATA_DIR / "path1.path"))
var0.set_footprint(1.3, 3.5, 0.0, 0.0)
var0.trajectory = traj0
var0.robot_id = 1
```

Setting `.trajectory` sweeps the footprint along the path and posts the swept-geometry domain
plus a minimum-duration constraint — see
[Trajectory envelopes](../concepts/trajectory-envelopes.md). A
[`Map`](../api/meta.spatio_temporal.paths.md) `MetaConstraint` is registered to detect conflicts
between different robots' envelopes, then `refine_trajectory_envelopes()` is called *before*
`backtrack()`:

```python
map_ = Map(None, None)
meta_solver.add_meta_constraint(map_)

refined1 = meta_solver.refine_trajectory_envelopes()

solved = meta_solver.backtrack()
if solved:
    print(f"Added resolvers:\n{meta_solver.get_added_resolvers()}")
```

Refinement splits each envelope into ground envelopes around the region where it overlaps the
other robot's swept path, shrinking the spatial (and temporal) extent that a conflict-resolving
precedence constraint has to cover; `backtrack()` then finds and orders those constraints the
usual meta-CSP way (see [Meta-CSP architecture](../concepts/meta-csp-architecture.md)).
`print_info` in the script shows each ground envelope's transit times (`dts`) and completion
times (`cts`) before and after solving.

See also: [Spatial reasoning](../concepts/spatial-reasoning.md).
