# metacsp

Python port of the [Meta-CSP Framework](https://github.com/FedericoPecora/meta-csp-framework)
by Federico Pecora — a library for meta-CSP based hybrid constraint reasoning: simple temporal
problems (STP), Allen interval algebra (crisp and fuzzy), resource scheduling, spatial reasoning
(DE9IM, RCC, rectangle/block algebra), Boolean satisfiability, trajectory envelopes and
spatio-temporal path scheduling, plus online sensing and dispatching.

Backed by native-code libraries: numpy (temporal propagation), Shapely/GEOS (geometry — GEOS
is itself the C++ port of the JTS library the Java original used), PySAT (SAT solving), and
sympy (CNF conversion).

New to the codebase? Start at [Getting Started](getting-started.md), read the
[Concepts](concepts/constraint-networks.md) for the theory behind each solver, or jump straight
to the [API Reference](api/framework.md).

## Status

| Feature area | Java package | Python module |
|---|---|---|
| Utilities (logging, math, graph) | `utility/` | `metacsp.utility` |
| Framework core & meta-CSP search | `framework/` | `metacsp.framework` |
| Simple temporal problems (STP/APSP) | `time/` | `metacsp.time` |
| Allen interval algebra (crisp & fuzzy) | `multi/allenInterval/`, `fuzzyAllenInterval/` | `metacsp.multi.allen_interval`, `metacsp.fuzzy_allen_interval` |
| Activities & timelines | `multi/activity/` | `metacsp.multi.activity` |
| Symbolic variables & Boolean SAT | `multi/symbols/`, `booleanSAT/` | `metacsp.multi.symbols`, `metacsp.boolean_sat` |
| Spatial geometry & constraint solving | `spatial/geometry/` | `metacsp.spatial.geometry` |
| RCC, cardinal direction, reachability | `spatial/{RCC,cardinal,reachability}/` | `metacsp.spatial.{rcc,cardinal,reachability}` |
| DE9IM spatial relations | `multi/spatial/DE9IM/` | `metacsp.multi.spatial.de9im` |
| Rectangle/block/temporal-rectangle algebras | `multi/spatial/{rectangleAlgebra,blockAlgebra}/` | `metacsp.multi.spatial.{rectangle_algebra,block_algebra}` |
| Trajectory envelopes | `multi/spatioTemporal/` | `metacsp.multi.spatio_temporal` |
| Meta TCSP & resource schedulers | `meta/TCSP/`, `meta/symbolsAndTime/` | `metacsp.meta.tcsp`, `metacsp.meta.symbols_and_time` |
| Simple planner & hybrid planner | `meta/simplePlanner/`, `meta/hybridPlanner/` | `metacsp.meta.simple_planner`, `metacsp.meta.hybrid_planner` |
| Trajectory envelope scheduler | `meta/spatioTemporal/paths/` | `metacsp.meta.spatio_temporal.paths` |
| Sensing & dispatching | `sensing/`, `dispatching/` | `metacsp.sensing`, `metacsp.dispatching` |
| Online monitoring (fuzzy hypothesis inference) | `onLineMonitoring/` | `metacsp.online_monitoring` |
| JSON serialization (snapshot/delta) | — (new) | `metacsp.serialization` |
| Live viewer (dearpygui, replaces Swing) | `utility/UI/`, `utility/timelinePlotting/` | `metacsp.viz` (`viz` extra) |

## License

MIT — see [LICENSE](https://github.com/jack-mcmurdo/metacsp/blob/master/LICENSE). Original Java
framework © Federico Pecora.
