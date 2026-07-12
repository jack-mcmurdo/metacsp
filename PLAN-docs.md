# Plan: Documentation site for metacsp

**Goal:** A documentation wiki for the `metacsp` package (this repo), built with
MkDocs Material + mkdocstrings, living in `docs/`, deployed to Cloudflare Pages on every push
to `master`. Audience: newcomers **with** a Planning & Scheduling background — each concept
page states the theory (STP, Allen algebra, timelines, meta-CSP) tersely and links straight to
the auto-generated API pages of the classes implementing it. Tone everywhere: precise, enough
to get started, **no filler**.

## Protocol

**This is one milestone.** Implement the sections below in order in a single pass; the
Cloudflare deployment section is performed by the user in the dashboard (the agent's part is
only verifying the build command works locally). Run `mkdocs build --strict` (must exit 0, no
warnings) after each section; the docstring audit additionally needs `black src` + `pytest`
(it touches library files). Commit as you go with `docs: <one line>` messages (distinct from
PLAN.md's `M<n>` commits); tick checkboxes here as sections complete.

## Decisions (already made — do not revisit)

- **Generator:** MkDocs Material + mkdocstrings (`mkdocstrings[python]`, griffe static
  analysis — the `metacsp.viz` import guard is therefore harmless; dearpygui is **not** a docs
  dependency).
- **Location:** `docs/` in this repo (MkDocs default `docs_dir`); `mkdocs.yml` at repo root.
  The existing `docs/VIZ.md` becomes a site page, unchanged.
- **Deployment:** Cloudflare Pages connected to the GitHub repo
  (`jack-mcmurdo/metacsp`), auto-deploy on push to `master`, custom subdomain via
  Cloudflare DNS.
- **Docstring style:** Google style for anything newly written (`docstring_style: google` in
  mkdocs.yml). Existing docstrings use prose with ``double-backtick`` literals — valid Markdown
  code spans; do **not** rewrite them for style.
- **API page granularity:** one page per leaf package, containing a single
  `::: metacsp.<pkg>` directive. Every leaf `__init__.py` already defines `__all__`
  (verified), so mkdocstrings renders exactly the public re-exports.
- **Commands** (from repo root):
  - install: `pip install -e ".[docs]"`
  - live preview: `mkdocs serve`
  - build: `mkdocs build --strict` → output in `site/`

## Steps

### 1. Tooling & skeleton

- [x] `pyproject.toml`: add a `docs` extra next to `viz`/`dev` (same list style):
      `docs = ["mkdocs-material>=9.5", "mkdocstrings[python]>=0.24"]`. Do not touch `dev`.
- [x] `.gitignore`: add `site/`.
- [x] `mkdocs.yml` at repo root, exactly this (nav grows in later milestones; start with the
      pages that exist after this milestone):

```yaml
site_name: metacsp
site_description: >-
  Python port of the Meta-CSP Framework — meta-CSP based hybrid temporal,
  spatial, and resource constraint reasoning.
repo_url: https://github.com/jack-mcmurdo/metacsp
repo_name: jack-mcmurdo/metacsp

theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      toggle: { icon: material/brightness-7, name: Dark mode }
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      toggle: { icon: material/brightness-4, name: Light mode }
  features:
    - navigation.sections
    - navigation.top
    - content.code.copy

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: google
            members_order: source
            show_root_heading: false
            show_source: true
            separate_signature: true
            show_signature_annotations: true
            merge_init_into_class: true
            inherited_members: false
            filters: ["!^_"]

markdown_extensions:
  - admonition
  - pymdownx.superfences
  - pymdownx.highlight
  - toc:
      permalink: true

nav:
  - Home: index.md
  - Visualization protocol: VIZ.md
```

- [x] `docs/index.md`: temporary stub (`# metacsp` + one sentence); replaced in step 4.
- **Acceptance:** `pip install -e ".[docs]"` succeeds; `mkdocs build --strict` exits 0;
  `mkdocs serve` renders Home and the VIZ.md page.

### 2. API reference pages

- [x] Create `docs/api/`, one file per leaf package/module below. Each file is exactly three
      lines — an `# metacsp.<pkg>` heading, a blank line, and the directive — e.g.
      `docs/api/time.md`:

```markdown
# metacsp.time

::: metacsp.time
```

- [x] Files (filename → directive target):
      `exceptions.md` → `metacsp.exceptions`; `utility.md` → `metacsp.utility`;
      `framework.md` → `metacsp.framework`; `framework.multi.md` → `metacsp.framework.multi`;
      `framework.meta.md` → `metacsp.framework.meta`; `time.md` → `metacsp.time`;
      `time.qualitative.md` → `metacsp.time.qualitative`;
      `multi.allen_interval.md` → `metacsp.multi.allen_interval`;
      `multi.activity.md` → `metacsp.multi.activity`;
      `multi.symbols.md` → `metacsp.multi.symbols`; `multi.tcsp.md` → `metacsp.multi.tcsp`;
      `boolean_sat.md` → `metacsp.boolean_sat`; `fuzzy_symbols.md` → `metacsp.fuzzy_symbols`;
      `fuzzy_allen_interval.md` → `metacsp.fuzzy_allen_interval`;
      `multi.fuzzy_activity.md` → `metacsp.multi.fuzzy_activity`;
      `multi.fuzzy_set_activity.md` → `metacsp.multi.fuzzy_set_activity`;
      `spatial.geometry.md` → `metacsp.spatial.geometry`;
      `spatial.rcc.md` → `metacsp.spatial.rcc`;
      `spatial.cardinal.md` → `metacsp.spatial.cardinal`;
      `spatial.reachability.md` → `metacsp.spatial.reachability`;
      `spatial.utility.md` → `metacsp.spatial.utility`;
      `multi.spatial.de9im.md` → `metacsp.multi.spatial.de9im`;
      `multi.spatial.rectangle_algebra.md` → `metacsp.multi.spatial.rectangle_algebra`;
      `multi.spatial.block_algebra.md` → `metacsp.multi.spatial.block_algebra`;
      `multi.temporal_rectangle_algebra.md` → `metacsp.multi.temporal_rectangle_algebra`;
      `multi.spatio_temporal.md` → `metacsp.multi.spatio_temporal`;
      `multi.spatio_temporal.paths.md` → `metacsp.multi.spatio_temporal.paths`;
      `meta.tcsp.md` → `metacsp.meta.tcsp`;
      `meta.symbols_and_time.md` → `metacsp.meta.symbols_and_time`;
      `meta.simple_planner.md` → `metacsp.meta.simple_planner`;
      `meta.fuzzy_activity.md` → `metacsp.meta.fuzzy_activity`;
      `meta.spatio_temporal.paths.md` → `metacsp.meta.spatio_temporal.paths`;
      `meta.hybrid_planner.md` → `metacsp.meta.hybrid_planner`;
      `sensing.md` → `metacsp.sensing`; `dispatching.md` → `metacsp.dispatching`;
      `online_monitoring.md` → `metacsp.online_monitoring`;
      `serialization.md` → `metacsp.serialization`; `viz.md` → `metacsp.viz`.
- [x] Add to `mkdocs.yml` nav an `API Reference:` section grouped as:
      **Core framework** (exceptions, utility, framework, framework.multi, framework.meta),
      **Temporal** (time, time.qualitative, multi.allen_interval, multi.activity, multi.tcsp,
      fuzzy_allen_interval, multi.fuzzy_activity, multi.fuzzy_set_activity),
      **Symbols & SAT** (multi.symbols, boolean_sat, fuzzy_symbols),
      **Spatial** (spatial.geometry, spatial.rcc, spatial.cardinal, spatial.reachability,
      spatial.utility, multi.spatial.de9im, multi.spatial.rectangle_algebra,
      multi.spatial.block_algebra, multi.temporal_rectangle_algebra),
      **Spatio-temporal** (multi.spatio_temporal, multi.spatio_temporal.paths,
      meta.spatio_temporal.paths),
      **Meta solvers** (meta.tcsp, meta.symbols_and_time, meta.simple_planner,
      meta.fuzzy_activity, meta.hybrid_planner),
      **Runtime** (sensing, dispatching, online_monitoring),
      **Serialization & viz** (serialization, viz).
- **Acceptance:** `mkdocs build --strict` exits 0; spot-open `api/time.md` and
  `api/framework.md` under `mkdocs serve` — classes from `__all__` render with signatures.

### 3. Docstring audit

Module and class docstrings already exist everywhere (PLAN.md convention C6) and are good.
**Method/property docstrings are thin** (spot check: `time/apsp_solver.py` has ~4 docstrings
for a large class). Rules:

- Every public class: keep the existing docstring; append nothing unless it lacks a
  one-sentence "what this is" opener.
- Every public method/property on the priority classes: one-line docstring minimum; Google
  `Args:`/`Returns:` only where the signature isn't self-explanatory. No filler
  ("This method…" phrasing banned).
- Do not restyle existing prose or ``double-backtick`` literals; do not rename anything
  (nomenclature fidelity to the Java original is a standing constraint).

- [x] **Priority (concept-page-linked) modules — full method/property pass:**
      `src/metacsp/framework/` (`Variable`, `Constraint`, `ConstraintNetwork`,
      `ConstraintSolver`, `Domain`), `src/metacsp/framework/multi/`,
      `src/metacsp/framework/meta/` (`MetaConstraint`, `MetaConstraintSolver`,
      `MetaVariable`), `src/metacsp/time/` (`APSPSolver`, `Bounds`,
      `SimpleDistanceConstraint`, `TimePoint`), `src/metacsp/time/qualitative/`,
      `src/metacsp/multi/allen_interval/`, `src/metacsp/multi/activity/`,
      `src/metacsp/multi/symbols/`, `src/metacsp/boolean_sat/`,
      `src/metacsp/meta/symbols_and_time/` (`Schedulable`, `ReusableResource`,
      `StateVariable`, `Scheduler`, `SymbolicTimeline`), `src/metacsp/meta/simple_planner/`,
      `src/metacsp/meta/tcsp/`, `src/metacsp/multi/spatio_temporal/paths/`,
      `src/metacsp/meta/spatio_temporal/paths/`, `src/metacsp/sensing/`,
      `src/metacsp/dispatching/`, `src/metacsp/serialization.py`.
- [x] **Secondary — class-docstring check only, fix gaps:** `fuzzy_*`, `spatial/*`,
      `multi/spatial/*`, `multi/temporal_rectangle_algebra/`, `multi/tcsp/`,
      `meta/hybrid_planner/`, `meta/fuzzy_activity/`, `online_monitoring/`, `viz/`,
      `utility/`, `exceptions.py`.
- **Acceptance:** `black src` clean, `pytest` green, `mkdocs build --strict` exits 0; on the
  rendered `api/time.md`, `api/framework.md`, `api/framework.meta.md`,
  `api/meta.symbols_and_time.md` pages, every listed public method shows a description.

### 4. Home + Getting Started

- [x] `docs/index.md`: what metacsp is (3–4 sentences, adapted from README intro), the
      feature table from `README.md` (Java package → Python module columns), links to Getting
      Started / Concepts / API Reference, license line.
- [x] `docs/getting-started.md`:
      1. Install (`pip install -e ".[dev]"` from a clone; note `viz` extra).
      2. First solver — the README APSP quickstart extended to ~20 lines: create
         `APSPSolver(0, 1000)`, two variables, one `SimpleDistanceConstraint`, print
         consistency **and** the resulting `TimePoint` bounds.
      3. Running examples: `python examples/test_apsp_solver.py`, pointer to
         `examples/tutorial/` and `examples/SKIPPED.md`.
      4. Logging: `metacsp.utility.logging.set_level` two-liner.
      Each code identifier links to its `api/` page.
- [x] Nav: insert `Getting Started: getting-started.md` after Home.
- **Acceptance:** `mkdocs build --strict` exits 0; the Getting Started snippet is pasted into
  `python` and runs as shown.

### 5. Concept pages

One page per core concept in `docs/concepts/`. Per page: (a) the P&S theory in a few short
paragraphs — definitions, not tutorials; (b) how this codebase realizes it; (c) an
**API** section linking every named class to its `api/` page; (d) a **See also** line linking
the relevant example walkthrough (created in step 6 — use the final paths now).
Target length ≤ ~120 lines each.

- [x] `concepts/constraint-networks.md` — CSP recap (variables, domains, constraints,
      consistency); `Variable`, `Domain`, `Constraint`/`BinaryConstraint`,
      `ConstraintNetwork` (graph-backed, change listeners), `ConstraintSolver` contract.
- [x] `concepts/meta-csp-architecture.md` — the meta-CSP idea: a ground CSP plus
      meta-constraints that detect flaws and propose resolvers; backtracking search over
      meta-variables; multi-level variables. `MultiVariable`, `MultiConstraint`,
      `MultiConstraintSolver`, `MetaConstraint`, `MetaVariable`, `MetaConstraintSolver`.
- [x] `concepts/temporal-reasoning.md` — STP theory: distance graph, negative cycles ⇔
      inconsistency, APSP/Floyd–Warshall propagation, earliest/latest times; TCSP as
      disjunctive STP solved by meta-search. `APSPSolver`, `TimePoint`, `Bounds`,
      `SimpleDistanceConstraint`, `Interval`; `DistanceConstraintSolver`, `MultiTimePoint`
      (multi.tcsp); `TCSPSolver`, `TCSPLabeling` (meta.tcsp).
- [x] `concepts/allen-interval-algebra.md` — the 13 qualitative relations, path consistency;
      quantitative Allen constraints compiled to STP bounds; fuzzy variant (possibility
      degrees). `QualitativeAllenIntervalConstraint`, `QualitativeAllenSolver`,
      `SimpleAllenInterval`; `AllenInterval`, `AllenIntervalConstraint`,
      `AllenIntervalNetworkSolver`; `FuzzyAllenIntervalConstraint`,
      `FuzzyAllenIntervalNetworkSolver`.
- [x] `concepts/activities-and-timelines.md` — activities = symbolic value + flexible
      temporal interval; symbolic variables grounded in SAT; timelines as the evolution of a
      component's value over pulses; symbolic timelines extracted after solving.
      `SymbolicVariableActivity`, `ActivityNetworkSolver`, `Timeline` (multi.activity);
      `SymbolicVariable`, `SymbolicVariableConstraintSolver` (multi.symbols);
      `BooleanVariable`, `BooleanSatisfiabilitySolver` (boolean_sat); `SymbolicTimeline`
      (meta.symbols_and_time).
- [x] `concepts/scheduling-and-planning.md` — meta-constraints as schedulers/planners:
      resource conflicts (peak collection, MCS) resolved by precedence constraints;
      state-variable scheduling; operator-based planning on timelines. `Schedulable`,
      `ReusableResource`, `StateVariable`, `StateVariableScheduler`, `Scheduler`
      (meta.symbols_and_time); `SimplePlanner`, `SimpleDomain`, `SimpleOperator`,
      `PlanningOperator` (meta.simple_planner); one paragraph on `SimpleHybridPlanner`
      (meta.hybrid_planner) with links.
- [x] `concepts/spatial-reasoning.md` — qualitative spatial calculi: RCC, cardinal
      directions, DE9IM intersection matrices, rectangle/block algebra (interval algebra
      lifted to axes), plus the metric geometry layer. `RCCConstraint`,
      `RCCConstraintSolver`; `CardinalConstraint`; `DE9IMRelation`, `DE9IMRelationSolver`;
      `RectangleConstraintSolver`, `UnaryRectangleConstraint`; `BlockConstraintSolver`;
      `GeometricConstraintSolver` (spatial.geometry).
- [x] `concepts/trajectory-envelopes.md` — spatio-temporal envelopes: a path swept by a
      footprint, sliced into polygons with STP-bounded transit times; scheduling = meta-CSP
      resolving envelope overlaps with temporal orderings. `Pose`, `PoseSteering`,
      `Trajectory`, `TrajectoryEnvelope`, `TrajectoryEnvelopeSolver`
      (multi.spatio_temporal.paths); `Map`, `TrajectoryEnvelopeScheduler`
      (meta.spatio_temporal.paths).
- [x] `concepts/sensing-and-dispatching.md` — closing the loop: sensor traces asserted as
      activities, periodic re-inference, dispatching activities to executors.
      `Sensor`, `ConstraintNetworkAnimator`, `Controllable` (sensing); `Dispatcher`,
      `DispatchingFunction` (dispatching); one paragraph + links for `online_monitoring`.
- [x] Nav: `Concepts:` section listing the nine pages in the order above.
- **Acceptance:** `mkdocs build --strict` exits 0 (this also validates every cross-link);
  every class named on a concept page is a working link into `api/`.

### 6. Example walkthroughs + visualization placeholder

Walkthroughs annotate **existing** scripts in `examples/` — quote short excerpts, link the
full file on GitHub, never duplicate a whole script. One page per walkthrough in
`docs/examples/`:

- [x] `examples/index.md` — how to run (`python examples/<file>.py`), directory map
      (top-level / `multi/` / `meta/` / `tutorial/`), link to `examples/SKIPPED.md` on GitHub.
- [x] `examples/stp.md` — `examples/test_apsp_solver.py` (STP bounds propagation).
- [x] `examples/activities.md` — `examples/multi/test_activity_network_solver.py`
      (activities + Allen constraints + timeline extraction).
- [x] `examples/resource-scheduling.md` — `examples/meta/test_reusable_resource_scheduler.py`
      (meta-CSP conflict resolution end to end).
- [x] `examples/planning.md` — `examples/meta/test_simple_planner.py` (operator-based
      planning on timelines).
- [x] `examples/trajectory-envelopes.md` —
      `examples/meta/test_trajectory_envelope_scheduler.py` (envelope construction +
      scheduling; uses `tests/data/paths/` fixtures).
- [x] `examples/dispatching.md` —
      `examples/tutorial/dispatching/simple_dispatching_example.py` (interactive; document
      the stdin loop and what to type).
- [x] `docs/visualization.md` — **placeholder page, deliberately short**: state that
      `metacsp.viz` (dearpygui) is being replaced by a web-based frontend; link `VIZ.md`
      (the JSON snapshot/delta protocol, which is the stable contract) and `api/serialization.md`
      + `api/viz.md`. Add an `!!! note` that this page will be rewritten once the web viewer
      lands — **do not** document dearpygui workflows in depth.
- [x] Nav: `Examples:` section (index + six walkthroughs), then
      `Visualization: visualization.md`, then move `Visualization protocol: VIZ.md` beneath it.
- [x] Back-fill the `See also` example links on concept pages (step 5 wrote the paths; verify
      they resolve).
- **Acceptance:** `mkdocs build --strict` exits 0; each quoted excerpt matches the current
  script text (spot-check by grep).

### 7. Cloudflare Pages deployment (user-performed)

Local prerequisite (agent-verifiable): `pip install -e ".[docs]" && mkdocs build --strict`
succeeds from a clean venv — this is exactly what Cloudflare will run.

Dashboard steps (user):

1. Cloudflare dashboard → **Workers & Pages → Create → Pages → Connect to Git** → select the
   `jack-mcmurdo/metacsp` repo.
2. Production branch: `master`. Root directory: `/` (default).
3. Build command: `pip install -e ".[docs]" && mkdocs build`
   Build output directory: `site`
4. Environment variable (Production **and** Preview): `PYTHON_VERSION = 3.12` (matches the
   top of the CI matrix).
5. Save and deploy; confirm the `*.pages.dev` URL serves the site. Pushes to `master` now
   auto-deploy; other branches get preview URLs automatically.
6. Custom subdomain: Pages project → **Custom domains → Set up a custom domain** → enter the
   chosen subdomain (e.g. `metacsp.<your-cloudflare-managed-domain>`). Cloudflare creates the
   CNAME to `<project>.pages.dev` automatically since the zone is on Cloudflare DNS; wait for
   the certificate to go Active.
- **Acceptance:** the custom subdomain serves the site over HTTPS; a trivial docs commit to
  `master` redeploys automatically.

### 8. Review pass

- [x] **Tone sweep:** read every page in `docs/`; delete restating-the-obvious sentences,
      marketing adjectives, and any paragraph that doesn't teach or link. Concept pages stay
      ≤ ~120 lines.
- [x] **Link integrity:** `mkdocs build --strict` (broken internal links fail the build);
      additionally grep all `docs/**/*.md` for `http` links and spot-check the external ones
      (GitHub file links, upstream Java repo).
- [x] **Theory↔API cross-linking audit:** for each of the nine concept pages, confirm
      (a) every class it names links to its `api/` page, and (b) the class actually appears on
      that rendered page (i.e. it is in the package's `__all__`).
- [x] **Getting Started re-test:** paste and run the quickstart snippet in a fresh venv with
      `pip install -e .` only.
- **Acceptance:** all four checks pass; final commit `docs: done`.

## Edge cases & risks

- **`mkdocs build --strict` from day one** — adding it late means a wall of warnings; every
  milestone's acceptance includes it.
- **griffe vs. runtime imports:** mkdocstrings analyzes `src/` statically, so `metacsp.viz`
  documents fine without dearpygui and no example/heavy import runs at build time. If a page
  ever errors, do not switch the handler to dynamic mode; fix the docstring/annotation instead.
- **`docs/VIZ.md` heading:** its H1 is "Visualization protocol"; keep the nav title identical
  to avoid two names for one page.
- **Nomenclature fidelity:** the docstring audit (D3) must not rename or re-signature anything
  — names track the Java original per PLAN.md C2; docs describe, never refactor.
- **Cloudflare pip cache:** if the Pages build ever picks a stale metacsp, the editable
  install (`-e`) sidesteps it; do not change to a wheel build.
