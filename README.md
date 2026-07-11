# metacsp

Python port of the [Meta-CSP Framework](https://github.com/FedericoPecora/meta-csp-framework)
by Federico Pecora — a library for meta-CSP based hybrid constraint reasoning: simple temporal
problems (STP), Allen interval algebra (crisp and fuzzy), resource scheduling, spatial reasoning
(DE9IM, RCC, rectangle/block algebra), Boolean satisfiability, trajectory envelopes and
spatio-temporal path scheduling, plus online sensing and dispatching.

Backed by native-code libraries: numpy (temporal propagation), Shapely/GEOS (geometry —
GEOS is itself the C++ port of the JTS library the Java original used), PySAT (SAT solving),
and sympy (CNF conversion).

## Install

```bash
pip install -e ".[dev]"      # development (tests, formatter)
pip install -e ".[viz]"      # optional matplotlib plotting
```

## Usage

Runnable demos live in `examples/` — plain Python scripts, e.g.:

```bash
python examples/test_apsp_solver.py
```

## Status

Under construction. The port is executed phase by phase per [PLAN.md](PLAN.md).

## License

MIT — see [LICENSE](LICENSE). Original Java framework © Federico Pecora.
