"""Port of examples/multi/TestConstraintNetworkAnimator.java.

The Java original visualizes progression forever via
``TimelineVisualizer.startAutomaticUpdate`` (a Swing timer that keeps the
JVM alive) -- replaced here by M21's ``metacsp.viz.timeline.TimelineWindow``
(dearpygui), attached to live-redraw on every D2 change event and run for a
bounded number of refreshes so the example exits instead of blocking
forever like the Java GUI does.
"""

from __future__ import annotations

import time
from pathlib import Path

from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.sensing.sensor import Sensor
from metacsp.viz.app import VizApp
from metacsp.viz.timeline import TimelineWindow

_DATA_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "sensorTraces"
_RUN_SECONDS = 5.0
_REFRESH_INTERVAL_S = 0.5


def main() -> None:
    ans = ActivityNetworkSolver(0, 100000)
    animator = ConstraintNetworkAnimator(ans, 1000)

    sensor_a = Sensor("SensorA", animator)
    sensor_b = Sensor("SensorB", animator)
    sensor_a.register_sensor_trace(str(_DATA_DIR / "sensorA.st"))
    sensor_b.register_sensor_trace(str(_DATA_DIR / "sensorB.st"))

    app = VizApp(title="TestConstraintNetworkAnimator")
    window = TimelineWindow(ans.constraint_network, ["Time", "SensorA", "SensorB"])
    app.create()
    window.build(app)
    window.attach()
    try:
        deadline = time.monotonic() + _RUN_SECONDS
        while time.monotonic() < deadline:
            window.refresh()
            time.sleep(_REFRESH_INTERVAL_S)
    finally:
        window.destroy()
        app.destroy()
        animator.teardown()


if __name__ == "__main__":
    main()
