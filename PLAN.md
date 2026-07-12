# Plan: Full Python port of the Meta-CSP Framework

**Goal:** Port the Java Meta-CSP Framework (`org.metacsp`, ~36k LOC of library code) to a
Python package `metacsp` (this repo, `src/` layout), replacing the Swing UI with a
JSON-serialization + observer layer so a browser-based viewer can be added later.

## Milestone progress

- [x] M0 — repo scaffold (pyproject, CI, release workflow, package skeleton)
- [x] M1 — utilities: exceptions, logging, math, graph
- [x] M2 — framework core
- [x] M3 — framework.multi machinery
- [x] M4 — framework.meta machinery
- [x] M5 — temporal core (time, time.qualitative)
- [x] M6 — Allen intervals & activities
- [x] M7 — symbolic variables & multi TCSP
- [x] M8 — Boolean SAT
- [x] M9 — fuzzy solvers
- [ ] M10 — spatial geometry & geometric constraint solving
- [ ] M11 — RCC, cardinal, reachability
- [ ] M12 — DE9IM spatial relations
- [ ] M13 — rectangle, block & temporal-rectangle algebras
- [ ] M14 — trajectory envelopes
- [ ] M15 — meta TCSP & resource schedulers
- [ ] M16 — simple planner & fuzzy-activity meta solver
- [ ] M17 — trajectory envelope scheduler
- [ ] M18 — hybrid planner
- [ ] M19 — sensing & dispatching
- [ ] M20 — online monitoring
- [ ] M21 — serialization, plotting, viz protocol doc
- [ ] M22 — examples sweep & README

**Known ordering exception (M6/M7/M8):** while implementing M6, `multi/activity/`'s
`SymbolicVariableActivity` and `ActivityNetworkSolver` turned out to depend on
`multi/symbols/` (M7), which in turn depends on `booleanSAT/` (M8) — a real dependency
chain `activity (M6) → symbols (M7) → booleanSAT (M8)` that the numeric milestone order
doesn't respect. Resolution: execute this range out of numeric order — **M8, then M7,
then the remainder of M6** — checking each off `[x]` as its own content is completed
regardless of visitation order, then continue numerically from M9. `multi/allen_interval/`
and the symbols-free parts of `multi/activity/` (`Activity`, `ActivityComparator`,
`Timeline`) have no such dependency and are implemented as part of M6 directly.

## Agent protocol

1. Pick the **first unchecked** milestone above, respecting the M6/M7/M8 ordering
   exception noted there.
2. Implement only that milestone, following the conventions and decisions below.
3. Run `black src tests examples && pytest` until the milestone's tests **and all previous
   tests** pass.
4. Commit the work: `git add -A && git commit -m "M<n>: <one line of what was built>"`.
5. Mark the milestone `[x]` in **Milestone progress** and commit: `M<n>: done`.
6. **Stop.** One milestone per session.

Milestones are dependency-ordered: each is functional and testable given only the milestones
before it. Do not start a later milestone early, and do not partially implement a future one.

## Reference source (read-only, the porting oracle)

```bash
git clone --depth 1 https://github.com/FedericoPecora/meta-csp-framework /tmp/metacsp-java
```

Pinned commit: `6eb822340b2761e65988b1b9529ede7abeca2832`. All Java paths below are relative to
`/tmp/metacsp-java/src/main/java/org/metacsp/`. When this plan and the Java source disagree on
behavior, **the Java source wins** — replicate its observable behavior exactly (same
consistency verdicts, same bounds values, same solver decisions), not its style.

## Already scaffolded (M0) — do not recreate

`pyproject.toml` (deps: numpy, shapely, python-sat, sympy; extras `viz`=matplotlib, `dev`),
`LICENSE`, `README.md`, `.gitignore`, `.github/workflows/{ci,release}.yml`,
`src/metacsp/__init__.py`, `tests/test_smoke.py`, `examples/README.md`. CI runs
`black --check src tests examples` and `pytest` on Python 3.10–3.12. Keep all new code
black-formatted (line length 100).

## Porting conventions (apply everywhere, no exceptions)

- **C1 — File layout:** one Python module per Java class, file named as the snake_case of the
  class name, placed in the package mapped by the Module Map below. Every package
  `__init__.py` re-exports its public classes. Exception: the whole `throwables/` package
  becomes the single module `metacsp/exceptions.py`.
- **C2 — Names:** class names unchanged (CamelCase). Methods and variables camelCase →
  snake_case. `getFoo()` → property `foo`; `setFoo(v)` → property setter; `isFoo()` →
  property `is_foo`. Java constants stay UPPER_SNAKE class attributes.
- **C3 — Object protocol:** `equals`/`hashCode` → `__eq__`/`__hash__` with the same identity
  semantics as the Java class (most compare by integer ID); `toString` → `__str__`;
  `compareTo`/`Comparator` → `__lt__` + `functools.total_ordering` or a `key=` function.
- **C4 — Abstract classes** → `abc.ABC` with `@abstractmethod`. Single-method callback
  interfaces (`ConstraintNetworkChangeListener`, `InferenceCallback`, `PeriodicCallback`,
  `HypothesisListener`, `DispatchingFunction`'s callback) → accept any Python callable;
  document the expected signature in the docstring.
- **C5 — Reflection removal:** wherever Java passes `Class<?>` objects and calls
  `getConstructor(...).newInstance(...)` (in `framework/ConstraintNetwork.java`,
  `framework/Variable.java`, `framework/multi/MultiVariable.java`,
  `framework/multi/MultiConstraintSolver.java`, `multi/spatial/DE9IM/DE9IMRelation.java`),
  pass the Python class object itself and call it. Constructor-signature lookup tables become
  explicit factory classmethods or `**kwargs`.
- **C6 — Typing & docs:** `from __future__ import annotations` and full type hints in every
  module. Every ported class's docstring names its Java source file
  (e.g. `"""Port of framework/ConstraintNetwork.java."""`).
- **C7 — Determinism:** Java iterates `HashSet`/`HashMap` in unspecified order; Python must use
  insertion-ordered `dict`/`list` (never `set` where iteration order can affect solver
  decisions). This makes runs reproducible; exact tie-breaking may differ from Java — that is
  acceptable as long as final consistency verdicts and bounds match.
- **C8 — No prints in library code**; use the logging wrapper (D7). Examples may print.
- **C9 — Time units:** keep milliseconds wherever Java uses them (periods, horizons).
- **C10 — Java object serialization** (`Serializable`, used to save/load constraint networks)
  → `save(path)`/`load(path)` using `pickle`. Do not port `readObject`/`writeObject` logic.

## Architecture decisions

- **D1 — Graph (replaces JUNG):** write `metacsp/utility/graph.py` by hand; no networkx.
  Two classes:
  - `DirectedSparseMultigraph[V, E]`: parallel edges allowed, edge objects are unique keys.
    API (mirroring the JUNG calls used in `framework/`): `add_vertex(v)`, `remove_vertex(v)`,
    `add_edge(e, src, dst)`, `remove_edge(e)`, `vertices()`, `edges()`, `contains_vertex(v)`,
    `contains_edge(e)`, `in_edges(v)`, `out_edges(v)`, `incident_edges(v)`, `source(e)`,
    `dest(e)`, `find_edge_set(src, dst)`, `predecessors(v)`, `successors(v)`.
  - `DelegateTree[V, E]`: rooted tree used by `MetaConstraintSolver` search and the
    variable/solver hierarchies: `set_root(v)`, `add_child(edge, parent, child)`, `parent(v)`,
    `children(v)`, `depth(v)`, `subtree(v)` (replaces JUNG `TreeUtils.getSubTree`).
- **D2 — Observer layer (replaces JUNG `ObservableGraph` + Swing repaints):**
  `ConstraintNetwork` gets `add_change_listener(cb)` / `remove_change_listener(cb)`; every
  variable/constraint add/remove fires `cb(event)` with a frozen dataclass
  `ConstraintNetworkChangeEvent(kind, payload)`, `kind` in
  `{"variable_added","variable_removed","constraint_added","constraint_removed"}`. This is the
  future browser-viz hook (see “Visualization protocol”).
- **D3 — APSP numerics (replaces `long[][]` in `time/APSPSolver.java`):** one
  `numpy.int64` matrix `dist` of shape `(2n, 2n)` (two timepoints per variable era as in Java —
  follow the Java layout exactly). Module constant `INF = 2**61` (Java uses
  `Long.MAX_VALUE - 1`; `2**61` leaves headroom so a vectorized three-term add
  `dist[:, i, None] + w + dist[j, None, :]` cannot overflow int64). After every add, clamp:
  `np.minimum(dist, INF, out=dist)`. Port the incremental propagation loops of
  `APSPSolver.java` as vectorized `np.minimum` broadcasts over the matrix; full Floyd–Warshall
  fallback (used on constraint removal) may use a plain triple loop expressed as `n` vectorized
  pivot steps. Pre-allocate capacity for `MAX_TPS` timepoints as the Java constructor does.
- **D4 — Geometry (replaces JTS 1.13):** Shapely ≥ 2.0 (GEOS — the C++ port of JTS itself, so
  semantics match 1:1). Mapping: `Geometry`→`shapely.geometry.base.BaseGeometry`,
  `Polygon`→`shapely.Polygon`, `LineString`→`shapely.LineString`, `Point`→`shapely.Point`,
  `Coordinate`→`(x, y)` tuple, `GeometryFactory`→shapely constructors,
  `IntersectionMatrix`/`Geometry.relate()`→`shapely` `relate()` / `relate_pattern()`.
  The self-contained physics/geometry code in `spatial/geometry/` (Vec2, Mat2, polygon
  collision, Sutherland–Hodgman clipping) is ported mechanically with numpy — do **not**
  replace it with shapely; it implements its own algorithms that `GeometricConstraintSolver`
  depends on.
- **D5 — SAT (replaces SAT4J):** `pysat.solvers.Minisat22` via the `python-sat` package.
  `BooleanVariable` with internal ID `n` ↔ DIMACS literal `n` (positive) / `-n` (negated).
  Mirror `booleanSAT/BooleanSatisfiabilitySolver.java`'s model enumeration by adding blocking
  clauses after each model, exactly as the Java class does.
- **D6 — CNF/WFF parsing (replaces aima-core):** `BooleanConstraint.create_boolean_constraints
  (vars, wff)` accepts the same WFF syntax as the Java version (see
  `examples/TestBooleanSatisfiabilitySolverSATNonCNF.java`): tokens `~` (not), `^` (and),
  `v` (or), `->` (implies), `<->` (iff), parentheses, and variable placeholders `x1..xN` bound
  positionally to the `vars` array. Implement by tokenizing and translating to a
  `sympy` boolean expression (`~`→`Not`, `^`→`And`, `v`→`Or`, `->`→`Implies`,
  `<->`→`Equivalent`), then `sympy.logic.boolalg.to_cnf(expr, simplify=False)`, then emitting
  one `BooleanConstraint` per CNF clause exactly as the Java factory does. Beware: `v` is an
  operator token, so variable placeholders are matched as `x<digits>` only.
- **D7 — Logging (replaces `utility/logging/MetaCSPLogging.java`):**
  `metacsp/utility/logging.py` wrapping stdlib `logging`: `get_logger(cls)` returns
  `logging.getLogger(f"metacsp.{cls.__name__}")`; `set_level(level)` and
  `set_level_for(cls, level)` mirror the Java API. Do not port `LogBrowser`/`LinePainter`
  (Swing log viewer).
- **D8 — Math utilities:** `utility/{Binomial,Combination,Permutation,
  PermutationsWithRepetition,PowerSet,Gaussian,Matrix}.java` → single module
  `metacsp/utility/math.py` implemented with `itertools`/`numpy` but exposing the same
  function/class names.
- **D9 — Threads:** `sensing/ConstraintNetworkAnimator.java`, `dispatching/Dispatcher.java`,
  `sensing/Sensor.java`, `onLineMonitoring/*` keep their `while True: sleep(period_ms/1000)`
  loops on `threading.Thread(daemon=True)`. Same period semantics (ms).
- **D10 — Visualization:** no GUI is ported. M21 builds
  `metacsp/serialization.py` (JSON snapshot/delta) + optional matplotlib plots
  (`metacsp/plot/`, import-guarded so `metacsp` works without matplotlib). Browser
  WebSocket+WebGL viewer is explicitly **future work, not in this plan** — only the protocol
  doc `docs/VIZ.md` is written now.

## Module map

| Java package (files) | Python module | Milestone |
|---|---|---|
| `throwables/`, `throwables/time/` (16) | `metacsp/exceptions.py` | M1 |
| `utility/logging/` (keep 2 of 4) | `metacsp/utility/logging.py` | M1 |
| `utility/*.java` math helpers (7) | `metacsp/utility/math.py` | M1 |
| — (new, replaces JUNG) | `metacsp/utility/graph.py` | M1 |
| `framework/` (16) | `metacsp/framework/` | M2 |
| `framework/multi/` (5) | `metacsp/framework/multi/` | M3 |
| `framework/meta/` (6) | `metacsp/framework/meta/` | M4 |
| `time/` (5) | `metacsp/time/` | M5 |
| `time/qualitative/` (4) | `metacsp/time/qualitative/` | M5 |
| `multi/allenInterval/` (4) | `metacsp/multi/allen_interval/` | M6 |
| `multi/activity/` (5) | `metacsp/multi/activity/` | M6 |
| `multi/symbols/` (3) | `metacsp/multi/symbols/` | M7 |
| `multi/TCSP/` (3) | `metacsp/multi/tcsp/` | M7 |
| `booleanSAT/` (4) | `metacsp/boolean_sat/` | M8 |
| `fuzzySymbols/` (3), `fuzzyAllenInterval/` (2) | `metacsp/fuzzy_symbols/`, `metacsp/fuzzy_allen_interval/` | M9 |
| `multi/fuzzyActivity/` (3), `multi/fuzzySetActivity/` (2) | `metacsp/multi/fuzzy_activity/`, `metacsp/multi/fuzzy_set_activity/` | M9 |
| `spatial/geometry/` (14) | `metacsp/spatial/geometry/` | M10 |
| `spatial/RCC/` (4), `spatial/cardinal/` (1), `spatial/reachability/` (4), `spatial/utility/` (3) | `metacsp/spatial/{rcc,cardinal,reachability,utility}/` | M11 |
| `multi/spatial/DE9IM/` (7) | `metacsp/multi/spatial/de9im/` | M12 |
| `multi/spatial/rectangleAlgebra/` (6), `blockAlgebra/` (5) | `metacsp/multi/spatial/{rectangle_algebra,block_algebra}/` | M13 |
| `multi/temporalRectangleAlgebra/` (4) | `metacsp/multi/temporal_rectangle_algebra/` | M13 |
| `multi/spatioTemporal/` (2), `multi/spatioTemporal/paths/` (6) | `metacsp/multi/spatio_temporal/`, `.../paths/` | M14 |
| `meta/TCSP/` (4) | `metacsp/meta/tcsp/` | M15 |
| `meta/symbolsAndTime/` (10) | `metacsp/meta/symbols_and_time/` | M15 |
| `meta/simplePlanner/` (8) | `metacsp/meta/simple_planner/` | M16 |
| `meta/fuzzyActivity/` (3) | `metacsp/meta/fuzzy_activity/` | M16 |
| `meta/spatioTemporal/paths/` (2) | `metacsp/meta/spatio_temporal/paths/` | M17 |
| `meta/hybridPlanner/` (8) | `metacsp/meta/hybrid_planner/` | M18 |
| `sensing/` (6), `dispatching/` (2) | `metacsp/sensing/`, `metacsp/dispatching/` | M19 |
| `onLineMonitoring/` (13, skip 3 `*OLD`) | `metacsp/online_monitoring/` | M20 |
| `utility/timelinePlotting/` (2) | `metacsp/plot/timeline.py` (matplotlib rewrite) | M21 |
| — (new) | `metacsp/serialization.py`, `docs/VIZ.md` | M21 |

## Skip list (do not port; note nothing else may be skipped)

- `utility/UI/` — all 21 Swing files. Their *purpose* is replaced by M21.
- `utility/logging/LogBrowser.java`, `LinePainter.java` — Swing.
- `multi/spatial/rectangleAlgebraNew/toRemove/` — dead code, marked for removal upstream.
- `multi/debugExample/` — debug scratch files.
- `onLineMonitoring/{SensorDataOLD,SensorRelationOLD,ValueOLD}.java` — dead code.
- `examples/**/CopyOf*.java` — editor copies.
- JUnit dependency — the Java `tests/` classes are ported to pytest (milestone steps below).

## Milestones

### M1 — Utilities
- [ ] `metacsp/exceptions.py`: one exception class per file in `throwables/` (same names).
- [ ] `metacsp/utility/logging.py` (D7), `metacsp/utility/math.py` (D8),
      `metacsp/utility/graph.py` (D1).
- [ ] `tests/test_graph.py`: parallel edges, removal cascades, tree subtree extraction.
- **Acceptance:** `pytest tests/test_graph.py` green.

### M2 — Framework core
- [x] `metacsp/framework/`: `Domain`, `Variable`, `Constraint`, `BinaryConstraint`,
      `ConstraintNetwork` (on `DirectedSparseMultigraph`, with D2 listeners),
      `ConstraintSolver`, `ConstraintNetworkChangeEvent`, `ValueChoiceFunction`,
      `ValueOrderingH`, `VariableOrderingH`, `ConstraintOrderingH`, `VariablePrototype`,
      `DummyVariable`, `DummyConstraint`, `ConstraintNetworkMarking`.
- [x] `tests/test_framework.py`: build a network of `DummyVariable`s, add/remove constraints,
      assert graph queries and that change listeners fire in order.
- **Acceptance:** `pytest tests/test_framework.py` green.

### M3 — framework.multi machinery
- [x] `metacsp/framework/multi/`: `MultiDomain`, `MultiVariable`, `MultiConstraint`,
      `MultiBinaryConstraint`, `MultiConstraintSolver` (reflection → C5 factories).
- [x] `tests/test_multi_framework.py`: construct a two-level `MultiVariable` solver with dummy
      internal solvers; assert variable creation cascades and constraint decomposition.
- **Acceptance:** tests green.

### M4 — framework.meta machinery
- [x] `metacsp/framework/meta/`: `MetaVariable`, `MetaConstraint`, `MetaConstraintSolver`
      (backtracking search on `DelegateTree`), `MultiMetaConstraint`, `FocusConstraint`,
      `NullConstraintNetwork`.
- [x] `tests/test_meta_framework.py`: a minimal meta-CSP (dummy meta constraint flagging a
      fabricated conflict with two resolvers) — assert backtracking explores and terminates.
- **Acceptance:** tests green. (Real end-to-end meta coverage arrives in M15.)

### M5 — Temporal core
- [x] `metacsp/time/`: `Bounds`, `Interval`, `TimePoint`, `SimpleDistanceConstraint`,
      `APSPSolver` per D3.
- [x] `metacsp/time/qualitative/`: `QualitativeAllenIntervalConstraint`, `SimpleInterval`,
      `SimpleAllenInterval`, `QualitativeAllenSolver` (path consistency).
- [x] Port Java `tests/TestAPSPSolver.java` and `tests/TestBounds.java` →
      `tests/test_apsp_solver.py`, `tests/test_bounds.py` (translate every JUnit assertion;
      the expected bounds values in those files are the oracle).
- [x] Port examples `examples/TestAPSPSolver*.java` (3 files),
      `TestQualitativeAllenConstraintSolver{,UNSAT}.java` → `examples/*.py`.
- **Acceptance:** ported JUnit assertions pass verbatim; each example runs clean via
  `python examples/<file>.py`.

### M6 — Allen intervals & activities
- [x] `metacsp/multi/allen_interval/` (incl. `AllenIntervalNetworkUtilities`),
      `metacsp/multi/activity/` (`SymbolicVariableActivity`, `ActivityNetworkSolver`,
      `Timeline`).
- [x] Port Java `tests/multi/{TestAllenInterval,TestAllenIntervalNetworkSolver,
      TestActivityNetworkSolver}.java` → pytest.
- [x] Port the `examples/multi/*.java` files that touch only these modules.
- **Acceptance:** ported assertions pass; examples run clean.

### M7 — Symbolic variables & multi TCSP
- [x] `metacsp/multi/symbols/` (`SymbolicVariableConstraintSolver` et al.),
      `metacsp/multi/tcsp/`.
- [x] `tests/test_symbols.py` from the symbolic-variable examples; port remaining
      `examples/multi/*.java` touching these modules.
- **Acceptance:** tests and examples green.

### M8 — Boolean SAT
- [x] `metacsp/boolean_sat/` per D5/D6.
- [x] Port Java `tests/TestBooleanSAT.java` → pytest; port the 9
      `examples/TestBooleanSatisfiabilitySolver*.java`.
- **Acceptance:** SAT/UNSAT verdicts match the Java assertions.

### M9 — Fuzzy solvers
- [x] `metacsp/fuzzy_symbols/`, `metacsp/fuzzy_allen_interval/`,
      `metacsp/multi/fuzzy_activity/`, `metacsp/multi/fuzzy_set_activity/`.
- [x] Port Java `tests/{TestFuzzyAllenIntervalNetworkSolver,
      TestFuzzySymbolicVariableConstraintSolver}.java` → pytest; port the 2 fuzzy examples
      (plus the 2 `examples/multi/TestFuzzy{Activity,SetActivity}NetworkSolver.java`).
- **Acceptance:** possibility degrees match the Java assertions.

### M10 — Spatial geometry & geometric constraint solving
- [ ] `metacsp/spatial/geometry/` (mechanical numpy port per D4 note, incl.
      `GeometricConstraintSolver`, `RCC2ConstraintSolver`).
- [ ] Port examples `TestGeometricConstraintSolver{,2}.java`, `TestRCC2ConstraintSolver.java`,
      `AckermannTest.java`; add `tests/test_geometry.py` asserting collision/clipping results
      on fixtures from those examples.
- **Acceptance:** tests and examples green.

### M11 — RCC, cardinal, reachability
- [ ] `metacsp/spatial/{rcc,cardinal,reachability,utility}/`.
- [ ] Port Java `tests/TestRCCConstraintNetworkSolver.java` → pytest; port example
      `TestRCCConstraintNetworkSolver.java`.
- **Acceptance:** relation verdicts equal the Java assertions.

### M12 — DE9IM spatial relations
- [ ] `metacsp/multi/spatial/de9im/` on shapely `relate_pattern` (D4).
- [ ] Port examples `TestDE9IMRelationSolver{,Simple}.java`; add `tests/test_de9im.py` from
      their asserted/printed relations.
- **Acceptance:** tests and examples green.

### M13 — Rectangle, block & temporal-rectangle algebras
- [ ] `metacsp/multi/spatial/{rectangle_algebra,block_algebra}/`,
      `metacsp/multi/temporal_rectangle_algebra/`.
- [ ] Port the `examples/multi/*.java` for these algebras; add `tests/test_rectangle_algebra.py`
      from their assertions.
- **Acceptance:** tests and examples green.

### M14 — Trajectory envelopes
- [ ] `metacsp/multi/spatio_temporal/` and `metacsp/multi/spatio_temporal/paths/`:
      `Pose`, `Trajectory`, `TrajectoryEnvelope`, `TrajectoryEnvelopeSolver` (shapely per D4).
      Copy the Java repo's `/tmp/metacsp-java/paths/` fixture files into `tests/data/paths/`.
- [ ] Port Java `tests/multi/TestPoseClass.java` → pytest; add
      `tests/test_trajectory_envelope.py` asserting envelope polygon areas and temporal bounds
      for one fixture trajectory from `tests/data/paths/`.
- **Acceptance:** tests green; a ported example builds envelopes end to end.

### M15 — Meta TCSP & resource schedulers
- [ ] `metacsp/meta/tcsp/`, `metacsp/meta/symbols_and_time/`.
- [ ] Port Java `tests/meta/TestReusableResourceScheduler.java` → pytest; port the scheduler
      examples from `examples/meta/`.
- **Acceptance:** scheduler finds conflict-free solutions on the ported tests.

### M16 — Simple planner & fuzzy-activity meta solver
- [ ] `metacsp/meta/simple_planner/`, `metacsp/meta/fuzzy_activity/`.
- [ ] Port the corresponding `examples/meta/*.java`; add `tests/test_simple_planner.py`
      asserting a plan is found on one ported domain.
- **Acceptance:** tests and examples green.

### M17 — Trajectory envelope scheduler
- [ ] `metacsp/meta/spatio_temporal/paths/` (`Map`, `TrajectoryEnvelopeScheduler`).
- [ ] Port examples `TestTrajectoryEnvelopeScheduler*.java` (non-viz ones); add
      `tests/test_te_scheduler.py` asserting a consistent, conflict-free result on one fixture.
- **Acceptance:** the scheduler example completes with a consistent network.

### M18 — Hybrid planner
- [ ] `metacsp/meta/hybrid_planner/`.
- [ ] Port its `examples/meta/*.java`; add `tests/test_hybrid_planner.py` from one example's
      outcome.
- **Acceptance:** tests and examples green.

### M19 — Sensing & dispatching
- [ ] `metacsp/sensing/` (`Sensor`, `ConstraintNetworkAnimator`, `Controllable`,
      `InferenceCallback`, `PeriodicCallback`, `NetworkMaintenanceError` → exceptions.py),
      `metacsp/dispatching/` (`Dispatcher`, `DispatchingFunction`), per D9. Copy
      `/tmp/metacsp-java/sensorTraces/` → `tests/data/sensorTraces/`.
- [ ] `tests/test_dispatching.py`: run an `ActivityNetworkSolver` + `Dispatcher` with a short
      period, assert activities are dispatched and finished in precedence order (poll with
      timeout; no bare sleeps in assertions).
- **Acceptance:** dispatch test green and deterministic.

### M20 — Online monitoring
- [ ] `metacsp/online_monitoring/` (10 files, skipping the 3 `*OLD`).
- [ ] `tests/test_online_monitoring.py`: feed a recorded sensor trace, assert the expected
      hypothesis emerges.
- **Acceptance:** tests green.

### M21 — Serialization, plotting, viz protocol doc
- [ ] `metacsp/serialization.py`: `network_to_dict(net)` →
      `{"variables": [{"id", "class", "domain": str}], "constraints": [{"class", "from",
      "to", "label": str}]}`; `timeline_to_dict`, `trajectory_envelope_to_dict` (GeoJSON-style
      geometry); `SnapshotPublisher(solver, period_ms, callback)` — a D9-style thread that
      calls `callback(json_str)` each period (the Java `TimelinePublisher`/
      `TimelineVisualizer` loop, minus Swing); delta events wired to D2 listeners.
- [ ] `metacsp/plot/timeline.py` (matplotlib, `viz` extra): timeline/Gantt plot equivalent to
      `utility/timelinePlotting` + `PlotActivityNetworkGantt`.
- [ ] `docs/VIZ.md`: document the JSON snapshot + delta message schema and the intended future
      browser stack (WebSocket server pushing `SnapshotPublisher` output + delta events to a
      WebGL/canvas viewer). **Viewer itself: future work, out of scope.**
- [ ] `tests/test_serialization.py`: round-trip a small activity network to dict, assert
      schema keys and delta events fire.
- **Acceptance:** tests green with and without matplotlib installed.

### M22 — Examples sweep & README
- [ ] Every remaining `examples/**/*.java` (non-skip-list) is ported to `examples/*.py`;
      formerly-Swing examples either plot via `metacsp.plot` or dump JSON via
      `metacsp.serialization`. Any example that cannot be meaningfully ported is listed in
      `examples/SKIPPED.md` with a one-line reason.
- [ ] README: replace the “Status” section with a feature table and a quickstart snippet.
- **Acceptance:** full `pytest` green on 3.10–3.12; `black --check` clean;
  `python examples/<each>.py` exits 0.

## Edge cases & risks

- **APSP overflow:** all int64 arithmetic near `INF` must clamp (D3); never subtract from a
  possibly-`INF` cell without a mask.
- **Search-order divergence (C7):** meta-CSP search may explore a different order than Java
  and return a *different valid solution*. Tests must assert solution validity/bounds, and
  copy Java's exact expected values only where the Java JUnit tests do.
- **Performance:** pure-Python meta search is expected to be slower than Java; acceptable for
  now. Keep `APSPSolver` fully vectorized — it dominates runtime. Do not micro-optimize
  elsewhere during the port.
- **`python-sat` import name** is `pysat`; don't confuse with the unrelated `pysat` PyPI
  package (already handled in pyproject: dependency is `python-sat`).
- **Shapely 2.x** geometries are immutable; where JTS code mutates coordinates in place,
  rebuild the geometry instead.
