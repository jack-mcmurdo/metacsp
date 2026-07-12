# Visualization

`metacsp.viz` is a browser-based live viewer: a websocket server
([`metacsp.viz.server.VizServer`](api/viz.md)) streams the wire protocol documented in
[Visualization protocol](VIZ.md) to a prebuilt Vite/React frontend, shipped inside the wheel so
end users never need Node. Install it with the `viz` extra:

```bash
pip install metacsp[viz]
```

## Usage

```python
from metacsp.viz import serve

server = serve(solver, ["Robot1", "Robot2"])  # opens a browser tab
...
server.stop()
```

`serve()` starts the server, opens a browser tab pointed at it, and returns the
[`VizServer`](api/viz.md) so you can `.stop()` it when done. See
`examples/viz_timeline_demo.py` for a runnable end-to-end demo, and
[`docs/VIZ.md`](VIZ.md) for the wire protocol if you want to build your own consumer.

## Views

- **Timeline** — an interactive Gantt view, one swimlane per component, colored by the four
  `SymbolicTimeline` interval states (gap/single/overlap/inconsistent). Supports zoom/pan,
  follow mode (autoscrolling to the latest pulse), hover tooltips, click-to-inspect, a
  component filter/reorder sidebar, and a history scrubber with playback over recorded frames.
- **Network** — the constraint network as a graph: nodes are variables, edges are binary
  constraints; non-binary constraints are listed alongside.
- **Map** — trajectory-envelope footprints (GeoJSON), shown only when the server was given
  `envelopes=[...]`.

Dark mode and light mode are both supported (follows your system preference, with a manual
toggle in the header).

## Building the frontend from source

Release wheels always ship a prebuilt frontend, but a source checkout needs one built manually:

```bash
npm --prefix frontend ci
npm --prefix frontend run build
```

`VizServer.start()`/`.run()` raise a clear `RuntimeError` with this instruction if
`src/metacsp/viz/static/` has no `index.html`.
