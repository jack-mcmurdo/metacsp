"""Port of examples/multi/TestSpatioTemporalVariableSolverOverlapsIntersects.java.

Two deviations from the literal Java source, both required to make this
example actually runnable rather than mechanically transcribing a bug:

- The Java original passes hardcoded, machine-specific absolute paths
  (``/home/fpa/paths/path1.path``) to ``Trajectory``; here the paths are
  resolved relative to this repo's ``tests/data/paths/`` fixtures (the
  same files, copied from the Java repo's ``paths/`` directory per PLAN.md).
- The Java original never calls ``setFootprint(...)`` on either variable
  before ``setTrajectory(...)``, which would unconditionally raise
  ``NoFootprintException`` (a real bug in the upstream example -- every
  other envelope-creation call site in the Java codebase sets a footprint
  first). A rectangular footprint is set here before building each
  trajectory, matching the pattern used everywhere else in the Java
  codebase (e.g. ``TrajectoryEnvelopeSolver.createEnvelopes``'s default
  footprint).

The Java original ends with a ``JTSDrawingPanel.drawVariables(...)`` call
(Swing, not ported -- see D10); dropped here.
"""

from __future__ import annotations

from pathlib import Path

from metacsp.framework.variable import Variable
from metacsp.multi.allen_interval import AllenIntervalConstraint
from metacsp.multi.spatio_temporal.paths import (
    Trajectory,
    TrajectoryEnvelope,
    TrajectoryEnvelopeSolver,
)
from metacsp.time.bounds import Bounds

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "paths"

# A simple rectangular footprint (meters), reference point at the origin.
_FOOTPRINT = ((1.0, -0.5), (1.0, 0.5), (-1.0, 0.5), (-1.0, -0.5))


def main() -> None:
    solver = TrajectoryEnvelopeSolver(0, 100000)
    vars_ = solver.create_variables(2)
    assert vars_ is not None
    var0 = vars_[0]
    var1 = vars_[1]
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)

    path0 = Trajectory(str(_DATA_DIR / "path1.path"))
    var0.set_footprint(*_FOOTPRINT)
    var0.trajectory = path0

    path1 = Trajectory(str(_DATA_DIR / "path3.path"))
    var1.set_footprint(*_FOOTPRINT)
    var1.trajectory = path1

    rel_var0 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(10, 10))
    rel_var0.from_ = var0
    rel_var0.to = var0

    dead_var0 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Deadline, Bounds(20, 20))
    dead_var0.from_ = var0
    dead_var0.to = var0

    rel_var1 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(15, 15))
    rel_var1.from_ = var1
    rel_var1.to = var1

    dead_var1 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Deadline, Bounds(25, 25))
    dead_var1.from_ = var1
    dead_var1.to = var1

    print(
        "Added constraints? "
        + str(solver.add_constraints(rel_var0, rel_var1, dead_var0, dead_var1))
    )

    print(f"path 0 has {var0.domain}")
    print(f"path 1 has {var1.domain}")

    print(solver.get_spatial_solver().get_all_implicit_relations())


if __name__ == "__main__":
    main()
