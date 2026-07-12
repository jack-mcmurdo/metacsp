"""Port of coordination/TestTrajectoryEnvelopeRepresentationThreeRobots.java
from the meta-csp-tutorial repo (M23).

The Java original ends with ``JTSDrawingPanel.drawConstraintNetwork`` and
``ConstraintNetwork.draw`` (Swing -- not ported, see D10); dropped here,
keeping the representation/printing logic. Paths resolved against this
repo's ``tests/data/paths/`` fixtures, per the precedent set in M22's
``examples/meta/test_trajectory_envelope_scheduler_three.py``.
"""

from __future__ import annotations

from pathlib import Path

from metacsp.multi.spatio_temporal.paths import (
    Trajectory,
    TrajectoryEnvelope,
    TrajectoryEnvelopeSolver,
)

_DATA_DIR = Path(__file__).resolve().parents[3] / "tests" / "data" / "paths"


def main() -> None:
    solver = TrajectoryEnvelopeSolver(0, 100000)
    vars_ = solver.create_variables(3)
    assert vars_ is not None
    var0, var1, var2 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)
    assert isinstance(var2, TrajectoryEnvelope)

    var0.set_footprint(2.3, 6.5, 0.0, 0.0)
    var0.trajectory = Trajectory(str(_DATA_DIR / "newpath1.path"))

    var1.set_footprint(2.3, 6.5, 0.0, 0.0)
    var1.trajectory = Trajectory(str(_DATA_DIR / "newpath2.path"))

    var2.set_footprint(2.3, 6.5, 0.0, 0.0)
    var2.trajectory = Trajectory(str(_DATA_DIR / "newpath3.path"))

    var0.robot_id = 1
    var1.robot_id = 2
    var2.robot_id = 3

    print("\n===================\n== VARIABLE INFO ==\n===================")
    print(f"\n{var0.info}")
    print(f"\n{var1.info}")
    print(f"\n{var2.info}")


if __name__ == "__main__":
    main()
