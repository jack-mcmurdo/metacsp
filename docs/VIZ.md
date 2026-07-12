# Visualization protocol

The webviz milestone replaces the in-process dearpygui viewer with a browser-based one: a
websocket server (`metacsp.viz.server.VizServer`) composes JSON messages from
`metacsp.serialization`'s functions and streams them to a prebuilt Vite/React frontend shipped
inside the wheel at `metacsp/viz/static/`. The three-layer architecture stays the same: core
fires D2 change events -> `metacsp.serialization` produces JSON -> the viewer consumes it. Only
the viewer layer changed.

## `metacsp.viz` (`viz` extra)

- `metacsp.viz.server.VizServer(solver, components, *, envelopes=None, period_ms=2000, host="127.0.0.1", port=8722)`
  -- owns one Starlette app: a `/ws` websocket endpoint plus (when the frontend has been built)
  the static frontend mounted at `/`. `start()` runs uvicorn in a daemon thread and returns once
  it's accepting connections; `run()` blocks; `stop()` removes the D2 change listener and shuts
  uvicorn down.
- `metacsp.viz.serve(solver, components, *, envelopes=None, period_ms=2000, host=..., port=..., open_browser=True)`
  -- convenience: constructs a `VizServer`, starts it, opens it in the system browser, and
  returns the server so the caller can `.stop()` it later.
- Import-guarded: `import metacsp.viz` raises a clear `ImportError` (not a bare
  `ModuleNotFoundError`) if `starlette`/`uvicorn` aren't installed, so the rest of `metacsp`
  stays usable headless.
- If `metacsp/viz/static/` has no `index.html` (a source checkout without a frontend build),
  `VizServer.start()`/`.run()` raise a `RuntimeError` telling the caller to run
  `npm --prefix frontend run build`. The `/ws` endpoint itself stays testable headlessly (e.g.
  via `starlette.testclient.TestClient`) regardless of whether the frontend has been built --
  only `start()`/`run()` enforce the build.

## Wire protocol v2

Every message is a JSON object with `"kind"`, a monotonic integer `"seq"`, and a unix-ms
integer `"ts"` (required by the frontend's history scrubber).

### `{"kind": "snapshot", ...}`

Sent once on client connect and every `period_ms` after that:

```json
{"kind": "snapshot", "seq": 1, "ts": 1700000000000,
 "variables": [ {"id", "class", "domain"}, ... ],
 "constraints": [ {"class", "from", "to", "label"}, ... ],
 "timelines": [ {"component", "pulses", "values"}, ... ],
 "envelopes": [ {"type": "Feature", "geometry", "properties"}, ... ]}
```

`constraints` is exactly `network_to_dict`'s `"constraints"` key (see `metacsp.serialization`).
`variables` is `network_to_dict`'s `"variables"` with one field added: `"component"` (the
variable's `Variable.component`, `null` if unset) -- needed by the frontend's click-to-inspect
panel to find the variables belonging to the component an interval came from, since
`variable_to_dict` itself (unchanged) has no such field. `timelines` is one
`timeline_to_dict(net, component)` per entry in the `components` list passed to `VizServer`.
`envelopes` is one `trajectory_envelope_to_dict` per entry in the `envelopes` list passed to
`VizServer` (empty if none were given).

### `{"kind": "delta", ...}`

Sent immediately per D2 change event (feeds the frontend's event log):

```json
{"kind": "delta", "seq": 2, "ts": 1700000000050,
 "event": "variable_added" | "variable_removed" | "constraint_added" | "constraint_removed",
 "variable": {...}}   // or "constraint": {...}, matching event.kind
```

`variable` also carries the added `"component"` field described above.

### `{"kind": "timelines", ...}`

Sent ~50 ms after a burst of change events settles (debounced), so the Gantt view updates live
without waiting for the next full snapshot:

```json
{"kind": "timelines", "seq": 3, "ts": 1700000000100,
 "timelines": [ {"component", "pulses", "values"}, ... ]}
```

Timelines are computed on the solver's own thread, inside the D2 change-listener callback --
not on the server's asyncio event loop thread -- since change listeners fire synchronously
right after a mutation is applied and before another mutation can start on that thread. This
sidesteps the risk of reading the constraint network concurrently with a solver mutating it;
only the resulting plain dicts cross the thread boundary.

### `{"kind": "command", ...}` (reserved, unimplemented)

An inbound message kind reserved for future solver control from the browser (e.g. pause/step).
v1 of the browser viewer is view-only: all interactivity (zoom, pan, filtering, the history
scrubber) is client-side state over the messages above, and the server does not currently read
anything sent by the client.

## `metacsp.serialization` (unchanged, still public API)

`SnapshotPublisher`, `variable_to_dict`, `constraint_to_dict`, `network_to_dict`,
`timeline_to_dict`, and `trajectory_envelope_to_dict` are untouched by this milestone --
`VizServer` composes its own messages from the same functions rather than wrapping
`SnapshotPublisher`. See the docstrings in `metacsp/serialization.py` for their schemas; the
snapshot section above documents how `VizServer` assembles them into protocol v2 messages.

## Frontend

`frontend/` (Vite + React + TypeScript + Tailwind + shadcn/ui) is built with
`npm --prefix frontend run build`, which outputs to `src/metacsp/viz/static/` (gitignored,
rebuilt on demand). Release wheels always ship a prebuilt `static/` (CI builds the frontend
before `python -m build`); end users installing from PyPI never need Node. `src/lib/protocol.ts`
mirrors this document's message shapes -- keep the two in sync when either changes.
