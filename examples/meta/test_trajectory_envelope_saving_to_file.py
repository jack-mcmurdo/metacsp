"""Port of examples/meta/TestTrajectoryEnvelopeSavingToFile.java.

Java object serialization (``ConstraintNetwork.saveConstraintNetwork``) is
not ported; per C10, ``ConstraintNetwork.save``/``.load`` use ``pickle``
instead. The Java original also opens a ``TrajectoryEnvelopeAnimator``
(Swing, not ported, see D10); dropped here. The network is saved to a
temporary directory rather than the Java original's repo-relative
``savedConstraintNetworks/example.cn``, so running this example doesn't
litter the repo; ``test_trajectory_envelope_serialization.py`` demonstrates
the matching load side of this same round trip.

The Java original's corner order for ``setFootprint`` is
``(backLeft, backRight, frontLeft, frontRight)``; passed straight through to
a polygon ring in that order, that traces a self-intersecting "bowtie" (the
diagonals backRight->frontLeft and frontRight->backLeft cross), which is
invalid input to the union operation ``TrajectoryEnvelope.trajectory``'s
setter performs when sweeping the footprint along the path -- GEOS raises
``TopologyException`` on it (older JTS apparently tolerated it; see D4).
Reordered here to ``(backLeft, backRight, frontRight, frontLeft)``, which
walks the rectangle's boundary consistently and is a valid simple polygon
with the same four corners.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from metacsp.meta.spatio_temporal.paths import Map, TrajectoryEnvelopeScheduler
from metacsp.multi.spatio_temporal.paths import Trajectory, TrajectoryEnvelope

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "paths"
_FRONT_LEFT = (1.8, 0.7)
_FRONT_RIGHT = (1.8, -0.7)
_BACK_RIGHT = (-1.8, -0.7)
_BACK_LEFT = (-1.8, 0.7)


def main() -> None:
    meta_solver = TrajectoryEnvelopeScheduler(0, 100000)
    solver = meta_solver.constraint_solvers[0]
    vars_ = solver.create_variables(2)
    assert vars_ is not None
    var0, var1 = vars_
    assert isinstance(var0, TrajectoryEnvelope)
    assert isinstance(var1, TrajectoryEnvelope)

    var0.set_footprint(_BACK_LEFT, _BACK_RIGHT, _FRONT_RIGHT, _FRONT_LEFT)
    var0.trajectory = Trajectory(str(_DATA_DIR / "path1.path"))

    var1.set_footprint(_BACK_LEFT, _BACK_RIGHT, _FRONT_RIGHT, _FRONT_LEFT)
    var1.trajectory = Trajectory(str(_DATA_DIR / "path3.path"))

    var0.robot_id = 1
    var1.robot_id = 2

    print(f"{var0} has domain {var0.domain}")
    print(f"{var1} has domain {var1.domain}")

    map_ = Map(None, None)
    meta_solver.add_meta_constraint(map_)

    refined1 = meta_solver.refine_trajectory_envelopes()
    print("REFINED:", refined1)

    solved = meta_solver.backtrack()
    print("Solved?", solved)
    if solved:
        print("Added resolvers:")
        print(meta_solver.get_added_resolvers())

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "example.pickle"
        solver.constraint_network.save(path)
        print(f"Saved constraint network to {path}")


if __name__ == "__main__":
    main()
