"""Port of examples/multi/TestConstraintNetworkAnimator.java.

The Java original visualizes progression forever via
``TimelineVisualizer.startAutomaticUpdate`` (a Swing timer that keeps the
JVM alive) -- replaced here by a bounded ``metacsp.viz.serve`` run, which
live-redraws on every D2 change event, so the example exits instead of
blocking forever like the Java GUI does.
"""

from __future__ import annotations

import time
from pathlib import Path

from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.sensing.sensor import Sensor
from metacsp.viz import serve

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "sensorTraces"
_RUN_SECONDS = 5.0


def main() -> None:
    ans = ActivityNetworkSolver(0, 100000)
    animator = ConstraintNetworkAnimator(ans, 1000)

    sensor_a = Sensor("SensorA", animator)
    sensor_b = Sensor("SensorB", animator)
    sensor_a.register_sensor_trace(str(_DATA_DIR / "sensorA.st"))
    sensor_b.register_sensor_trace(str(_DATA_DIR / "sensorB.st"))

    try:
        server = serve(ans, ["Time", "SensorA", "SensorB"])
    except RuntimeError as exc:
        print(f"(visualization unavailable: {exc})")
        server = None
    try:
        time.sleep(_RUN_SECONDS)
    finally:
        if server is not None:
            server.stop()
        animator.teardown()


if __name__ == "__main__":
    main()
