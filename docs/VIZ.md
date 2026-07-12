# Visualization protocol

M21 replaces the Java Swing UI (`utility/UI/`, `utility/timelinePlotting/`) with two things:

1. **`metacsp.viz`** — an in-scope live viewer built on [dearpygui](https://github.com/hoffstadt/DearPyGui),
   available via `pip install metacsp[viz]`. It subscribes directly to a `ConstraintNetwork`'s
   D2 change-listener stream (`add_change_listener`) and redraws in-process. This is what you
   want if you're running Python and want to watch a solver work.
2. **`metacsp.serialization`** — a JSON snapshot/delta format, decoupled from any particular
   renderer. This is the wire format for the live viewer's own updates, and is the intended
   integration point for a **future** out-of-process consumer (e.g. a browser-based
   WebSocket+WebGL viewer) — **not built by this plan**, but documented here so that future
   work has a stable contract to target without touching `metacsp` internals again.

## `metacsp.viz` (in scope, M21)

- `metacsp.viz.app.VizApp` — owns one dearpygui context/viewport. `create()` sets up the
  context without showing a window (used headlessly by `tests/test_viz.py`); `show()`/`run()`
  display it and block on the render loop.
- `metacsp.viz.timeline.TimelineWindow` — one Gantt row per component, built from that
  component's `SymbolicTimeline` (`meta/symbolsAndTime/SymbolicTimeline.java`, already ported in
  M15). Call `.attach()` to have it redraw itself on every D2 change event; call `.refresh()` to
  redraw once manually (e.g. from a `SnapshotPublisher` tick instead of/in addition to D2
  events).
- Both are import-guarded: `import metacsp.viz` raises a clear `ImportError` (not a bare
  `ModuleNotFoundError`) if `dearpygui` isn't installed, so the rest of `metacsp` stays usable
  headless.
- Geometry/trajectory canvas views (e.g. a live drawing of `TrajectoryEnvelope` footprints,
  replacing `utility/UI/JTSDrawingPanel.java`) are not built in M21 — `VizApp` exists precisely
  so a later view of that kind can be added without new bootstrap code.

## JSON snapshot/delta schema (`metacsp.serialization`)

Every message is a JSON object with a `"kind"` key.

### `variable_to_dict(v)`

```json
{"id": 3, "class": "SymbolicVariableActivity", "domain": "..."}
```

### `constraint_to_dict(c)`

```json
{"class": "AllenIntervalConstraint", "from": 3, "to": 5, "label": "..."}
```

`from`/`to` are variable ids; both are `null` for a constraint that is not a `BinaryConstraint`
(e.g. a masked/hyperedge constraint).

### `network_to_dict(net)` — a full snapshot

```json
{"variables": [ {"id", "class", "domain"}, ... ],
 "constraints": [ {"class", "from", "to", "label"}, ... ]}
```

### `timeline_to_dict(an, component)`

```json
{"component": "Robot1", "pulses": [0, 100, 200, 300], "values": [["A"], null, ["B"], null]}
```

`values[i]` is the list of symbols held by every activity active in `[pulses[i], pulses[i+1])`;
`null` means no activity holds there (`Timeline.is_undetermined`) — see
`multi/activity/Timeline.java`. `values` has the same length as `pulses`, with an
always-`null` trailing entry (mirrors the Java class's own array padding). An empty list `[]`
(as opposed to `null`) means `Timeline.is_inconsistent` — an activity's domain was restricted to
zero symbols.

### `trajectory_envelope_to_dict(te)` — GeoJSON-style

```json
{"type": "Feature",
 "geometry": {"type": "Polygon", "coordinates": [[[x, y], ...]]},
 "properties": {"id": 7, "component": "Robot1", "robot_id": 1,
                "symbols": ["Driving"], "est": 0, "eet": 12000}}
```

`geometry` is produced by `shapely.geometry.mapping()` on
`TrajectoryEnvelope.spatial_envelope.polygon` — the union of the envelope's footprint swept
along its path (see D4).

### `SnapshotPublisher(solver, period_ms, callback)`

A D9-style daemon thread (`start()`/`teardown()`) that calls `callback(json_str)`:

- once per `period_ms`, with a full snapshot: `{"kind": "snapshot", "variables": [...], "constraints": [...]}`
  (the keys of `network_to_dict`, plus `"kind"`).
- once per D2 change event, immediately (no waiting for the next tick): a delta message
  `{"kind": "delta", "event": "variable_added" | "variable_removed" | "constraint_added" | "constraint_removed",
  "variable": {...}}` (variable events) or `{"kind": "delta", "event": ..., "constraint": {...}}`
  (constraint events).

This replaces the publish role of `utility/timelinePlotting/TimelinePublisher.java` (which
instead rendered `SymbolicTimeline`s to PNG `BufferedImage`s on a background encoding thread);
the JSON format here carries the same underlying information without any image-encoding step,
so both `metacsp.viz` and a future out-of-process consumer can render it however they like.

## Future work (out of scope for this plan)

A browser-based viewer (WebSocket server pushing `SnapshotPublisher` output to a WebGL/canvas
frontend) is the natural next consumer of this schema, but is not built here. Anything
implementing it should only need this document and `metacsp.serialization`'s public functions —
no changes to `metacsp` core should be required.
