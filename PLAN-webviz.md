# Plan: Web-based visualization (replaces dearpygui)

**Goal:** Replace `metacsp.viz` (dearpygui) with a beautiful, interactive, browser-based live viewer — Vite + React + TS + Tailwind + shadcn/ui frontend, shipped prebuilt inside the PyPI wheel, fed by a websocket server wrapping the existing JSON serialization layer.

## Approach

Keep the three-layer architecture exactly as is: core fires change events → `metacsp.serialization` produces JSON → a viewer consumes it. Only the viewer layer changes. The dearpygui module (`viz/app.py`, `viz/timeline.py`) is deleted, not deprecated — v1.x is young enough to break this cleanly (bump to 1.1.0, note in release).

**Reference verdicts** (settled with user):
- *NASA Open MCT* — avoid. Telemetry-dashboard shape (data plots, mission control), wrong product.
- *NASA Aerie* — adapt interaction patterns only (zoom/pan/follow-mode UX); its view arrangement is not the target.
- *VS Code PDDL extension plan view* — adopt as the visual north star: swimlane Gantt, one row per component, colored interval blocks. Matches our `SymbolicTimeline` semantics directly.
- *Existing dearpygui view* — adopt its **semantics** (row per component, 4 interval states: gap/single/overlap/inconsistent), rebuild rendering and interaction entirely.

**Stack decisions:**
- Server: `starlette` + `uvicorn` (websocket + static file serving; FastAPI adds nothing we need). New `viz` extra: `["starlette>=0.37", "uvicorn>=0.29"]`, dearpygui removed everywhere.
- Frontend: Vite + React 18 + TypeScript + Tailwind v4 + shadcn/ui. Timeline rendered as **SVG** with `d3-scale` for time↔pixel mapping (typical problem sizes are tens of components / hundreds of intervals — SVG is plenty, and far easier for tooltips/transitions than canvas; revisit only if profiling demands). State via `zustand`. Constraint-graph view via `@xyflow/react` (React Flow).
- Packaging: `frontend/` at repo root; `vite build` outputs to `src/metacsp/viz/static/` (gitignored); hatchling `artifacts` forces it into the wheel; CI builds it before `python -m build`. End users never need Node.

**Protocol gap that must be fixed first (milestone 1):** `SnapshotPublisher` snapshots carry only `variables`/`constraints`; a browser cannot compute a `SymbolicTimeline` from `str(v.domain)`. The server therefore computes timelines server-side and pushes a new message kind. Wire protocol v2 (documented in `docs/VIZ.md`):
- All messages gain `"seq"` (monotonic int) and `"ts"` (unix ms) — required by the history scrubber.
- `{"kind": "snapshot", "variables": [...], "constraints": [...], "timelines": [timeline_to_dict...], "envelopes": [trajectory_envelope_to_dict...]}` — sent on client connect and every `period_ms`.
- `{"kind": "delta", "event": ..., "variable"|"constraint": {...}}` — unchanged, sent immediately per change event (feeds the event log).
- `{"kind": "timelines", "timelines": [...]}` — sent debounced (~50 ms) after change events, so the Gantt updates live without full snapshots.
- Inbound `{"kind": "command", ...}` is **reserved but unimplemented** (v1 is view-only; UI interactivity is all client-side).
- `SnapshotPublisher` in `serialization.py` stays untouched (still public API); the server composes its own messages from the same `*_to_dict` functions.

**Feature set (all in scope, priority order):** zoom + pan + adaptive time axis; follow mode (autoscroll tracking latest pulse, disengaged by manual pan, re-engaged by button); hover tooltips + click-to-inspect side panel; event-history scrubber with playback; component filter/reorder, legend, dark mode, animated transitions; constraint-network graph view; trajectory-envelope map view.

## Changes

- `src/metacsp/viz/__init__.py` — import guard now checks `starlette`/`uvicorn`; exports `VizServer`, `serve`.
- `src/metacsp/viz/server.py` — **new**: `VizServer` + `serve()` (replaces `app.py`/`timeline.py`, which are deleted).
- `src/metacsp/viz/static/` — **new, gitignored**: vite build output, shipped in wheel.
- `frontend/` — **new**: the entire Vite app.
- `pyproject.toml` — swap `viz`/`dev` extras; add hatchling `artifacts`; bump version 1.1.0.
- `docs/VIZ.md` — rewrite viewer section; document protocol v2.
- `tests/test_viz.py` — rewrite for the server (import guard, message composition, websocket roundtrip via `starlette.testclient` + `httpx` in dev extra).
- `.github/workflows/ci.yml`, `release.yml` — add Node steps.
- `examples/` — new `viz_timeline_demo.py` driving a solver with `serve()`.
- `.gitignore` — `src/metacsp/viz/static/`, `frontend/node_modules/`.

## Steps

### Milestone 1 — Server + protocol v2 (Python side complete, frontend-independent)
- [x] Delete `src/metacsp/viz/app.py`, `src/metacsp/viz/timeline.py`.
- [x] Write `src/metacsp/viz/server.py`:
  - `VizServer(solver, components: list[str], *, envelopes: list[TrajectoryEnvelope] | None = None, period_ms: int = 2000, host: str = "127.0.0.1", port: int = 8722)`.
  - Starlette app: `/ws` websocket endpoint; `StaticFiles` mounted at `/` from `metacsp/viz/static` via `importlib.resources` (if the dir is missing — source checkout without a frontend build — raise `RuntimeError` with the `npm --prefix frontend run build` instruction at startup, but keep `/ws` testable headlessly).
  - Thread bridge: the D2 change listener fires on the solver's thread → `loop.call_soon_threadsafe` into an `asyncio.Queue`; a consumer task broadcasts the delta immediately and schedules a debounced (50 ms) `timelines` message. Snapshot task ticks every `period_ms`. Monotonic `seq` on every outbound message.
  - On websocket connect: send one full snapshot before entering the broadcast loop.
  - `start()` (uvicorn in a daemon thread, returns immediately), `run()` (blocking), `stop()` (teardown: remove change listener, shut down uvicorn).
  - `serve(solver, components, *, open_browser=True, **kwargs)` convenience: constructs `VizServer`, `start()`, `webbrowser.open`, returns the server.
- [x] Update `src/metacsp/viz/__init__.py` import guard (starlette/uvicorn, same clear-`ImportError` contract as today).
- [x] `pyproject.toml`: `viz = ["starlette>=0.37", "uvicorn>=0.29"]`; `dev` drops dearpygui, gains starlette/uvicorn/httpx; add `[tool.hatch.build] artifacts = ["src/metacsp/viz/static/"]`.
- [x] Rewrite `tests/test_viz.py`: import-guard test; message-composition unit tests (snapshot includes `timelines` with correct pulses/values for a small ActivityNetworkSolver fixture; seq monotonic); websocket test via `starlette.testclient.TestClient` (connect → receive snapshot → add a constraint → receive delta + timelines).
- [x] Update `docs/VIZ.md`: protocol v2 as specced in Approach; mark `command` reserved.

### Milestone 2 — Frontend, views, packaging

**Scaffold**
- [x] `npm create vite@latest frontend -- --template react-ts`; Tailwind v4; `npx shadcn@latest init` (slate base, CSS variables, dark mode class strategy).
- [x] `vite.config.ts`: `build.outDir: "../src/metacsp/viz/static"`, `emptyOutDir: true`; dev server proxy `/ws` → `ws://127.0.0.1:8722`.
- [x] `src/lib/protocol.ts`: TS types mirroring `docs/VIZ.md` v2 exactly (single source of truth is the doc; keep a comment pointing at it).
- [x] `src/lib/ws.ts`: reconnecting websocket hook (exponential backoff, connection-status state).
- [x] `src/store.ts` (zustand): current snapshot, timelines, envelopes, event log (deltas), frame history (every `timelines`/`snapshot` message with seq+ts, ring buffer, cap ~2000 frames), UI state (viewport domain, follow flag, selected item, hidden components, live/scrub mode).
- [x] App shell with shadcn: header (title, connection badge, dark-mode toggle), tab bar (Timeline / Network / Map), collapsible right side panel (inspector).

**Timeline view core**
- [x] `TimelineView.tsx`: SVG swimlanes, one row per component (row order = `components` order, reorderable below). `d3-scale` `scaleLinear` time→x; interval rects from `values`/`pulses` with the four state colors (gap/single/overlap/inconsistent) mapped to a Tailwind-token palette that works in light+dark; symbol labels with overflow ellipsis, hidden below a min pixel width.
- [x] Adaptive time axis: tick density from the current zoom (`d3-scale .ticks()`), top-pinned ruler, faint vertical gridlines.
- [x] Zoom + pan: wheel-zoom anchored at cursor, drag-to-pan, pinch support; clamp to sane domain; implemented on the scale's domain in the store (not CSS transform) so axis/labels stay crisp.
- [x] Follow mode: when on, viewport right edge tracks `max(pulses)` on every update; any manual pan/zoom sets it off; shadcn toggle button ("Follow") re-engages. Default **on**.

**Interaction & polish**
- [x] Hover tooltip (shadcn tooltip or custom positioned div): interval symbols, `[start, end)` bounds, state.
- [x] Click-to-inspect: clicking an interval opens the side panel with the interval's details plus the variables/constraints from the current snapshot whose component matches; clicking empty space clears.
- [x] Component sidebar: checkbox list to hide/show rows, drag-to-reorder.
- [x] Legend (4 states), connection-lost overlay, empty-state screen ("waiting for solver…").
- [x] Animated transitions on interval change (CSS transition on x/width, ~150 ms) — no flicker-redraw.
- [x] Dark mode across all views; verify the 4-state palette in both themes.

**History scrubber**
- [x] Bottom bar: shadcn slider over the frame-history ring buffer + play/pause + speed (1×/4×/16×) + "Live" button.
- [x] Scrubbing renders the selected historical frame's timelines; entering scrub mode pauses live updates to the view (data still recorded); "Live" snaps back and re-enables follow.
- [x] Event log panel: scrollable delta list (seq, ts, event, item label); clicking an event jumps the scrubber to the nearest frame ≥ that seq.

**Network graph + envelope map views**
- [x] `NetworkView.tsx` (`@xyflow/react`): nodes = variables (id + class, colored by class), edges = binary constraints (label on hover); non-binary constraints listed in the side panel. Auto-layout with dagre or ELK; node click → inspector.
- [x] `MapView.tsx`: SVG polygons from envelope GeoJSON (planar coords, no projection needed), fill by component, label with symbols + `[est, eet]`; shared zoom/pan code from the timeline view; hidden tab when server sent no envelopes.

**Packaging, CI, example**
- [x] `.gitignore`: add `src/metacsp/viz/static/`, `frontend/node_modules/`.
- [x] `ci.yml`: new `frontend` job — `actions/setup-node@v4` (node 22, npm cache), `npm ci`, `npm run build` (template's `tsc -b && vite build` covers typecheck). While here: the push trigger says `branches: [main]` but the repo branch is `master` — fix to `[master]`.
- [x] `release.yml`: before "Build sdist and wheel", add setup-node + `npm --prefix frontend ci` + `npm --prefix frontend run build` so the wheel contains `static/`.
- [x] `examples/viz_timeline_demo.py`: small ActivityNetworkSolver scenario that adds activities/constraints on a timer thread and calls `serve(solver, components)` — gives a moving live demo.
- [x] Bump version to 1.1.0; update README viz section (screenshot placeholder, `pip install metacsp[viz]`, 3-line usage).
- [x] Verify end-to-end: `npm run build` → `pip install -e ".[viz]"` → run the example → browser shows live timeline; `python -m build` → unzip wheel → confirm `metacsp/viz/static/index.html` present.

## Edge cases & risks

- **Thread safety of timeline computation:** `timeline_to_dict` reads the constraint network from the server's asyncio thread while the solver mutates it. The 50 ms debounce narrows the window but doesn't close it; if tests show torn reads, compute timelines inside the change-listener callback (solver thread) and ship the dicts across the queue instead. Decide in milestone 1 based on the fixture test.
- **sdist installs:** an sdist built without the frontend produces a wheel without `static/`; the `RuntimeError` at `VizServer` startup with the npm instruction is the mitigation. Release wheels are always fine (CI builds frontend first).
- **Large problems:** hundreds of components would strain SVG. Out of scope for v1; the store/scale design keeps a canvas renderer swappable later.
- **Frame-history memory:** ring buffer capped (~2000 frames); oldest frames dropped, scrubber range shrinks accordingly.

## Open questions

None blocking. Deferred by design: inbound `command` protocol (solver control), canvas renderer, docs Visualization page (the PLAN-docs placeholder fills in after this lands).
