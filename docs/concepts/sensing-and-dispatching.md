# Sensing and dispatching

A planned schedule is only useful once it is connected to the real world: **sensing** asserts
observed readings into the constraint network as activities, so that re-inference (re-running a
planner/scheduler) can react to what actually happened; **dispatching** does the reverse,
handing off planned activities to the components responsible for executing them once their
earliest-start time has come. Both are driven by a single "Future" activity that advances in
wall-clock time — the moving marker against which "has this activity's start time arrived yet"
is checked — ticked periodically by a background loop.

A sensor reading changes the network by deadlining the previously-current activity for that
sensor's component and starting a new one, `Meets`-linked to Future; a dispatcher, on each tick,
overlaps a PLANNED activity with Future once its earliest start has passed, then calls a
per-component `DispatchingFunction` to actually act on it, tracking each activity through a
PLANNED → STARTED → FINISHING → FINISHED lifecycle.

## Realization in metacsp

`ConstraintNetworkAnimator` owns the Future activity and the background tick thread (a daemon
thread ticking every `period` ms); it optionally calls a registered inference callback
(e.g. to re-run a `SimplePlanner`, see [Scheduling and planning](scheduling-and-planning.md)) and
any extra periodic callbacks on every tick, and animates registered `Sensor` traces.
`Sensor.model_sensor_value` posts the `Deadline`/`Release` constraints described above;
`Controllable` tags a component as commandable and records the symbols it can be driven to.

`Dispatcher` runs its own background loop, one tick per `period` ms: for each registered
component, it walks that component's PLANNED activities in order, dispatches (via
`DispatchingFunction.dispatch`) whichever ones' earliest start has passed, and reacts to
`DispatchingFunction.skip`/`finish` to drive the ACTIVITY_STATE lifecycle. `DispatchingFunction`
is the abstract per-component hook applications implement.

`metacsp.online_monitoring` builds a similar sensing loop but for **hypothesis inference**:
`Rule`s combine `FuzzySensorEvent` readings into `Hypothesis`es about latent state, tracked as a
`HypothesisNode` dependency graph rather than posted directly as activities — see its module
docstring for the fuller picture, out of scope for this overview.

## API

- [`ConstraintNetworkAnimator`](../api/sensing.md) — drives Future forward and ticks
  sensors/callbacks.
- [`Sensor`](../api/sensing.md) / [`Controllable`](../api/sensing.md) — sensed and commandable
  components.
- [`Dispatcher`](../api/dispatching.md) /
  [`DispatchingFunction`](../api/dispatching.md) — periodic dispatch of PLANNED activities.

## See also

[Dispatching](../examples/dispatching.md) — an interactive dispatching example: what to type
and what happens.
