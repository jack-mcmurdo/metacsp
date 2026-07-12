"""Port of examples/meta/TestContextInference.java.

The Java original visualizes progression forever via
``TimelineVisualizer.startAutomaticUpdate`` (Swing) -- replaced here by a
bounded ``metacsp.viz.serve`` run so the example exits instead of blocking
forever like the Java GUI does.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import cast

from metacsp.meta.simple_planner import ProactivePlanningDomain
from metacsp.meta.simple_planner.simple_planner import SimplePlanner
from metacsp.meta.simple_planner.simple_planner_inference_callback import (
    SimplePlannerInferenceCallback,
)
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.sensing.sensor import Sensor
from metacsp.viz import serve

DOMAIN_FILE = (
    Path(__file__).resolve().parents[2] / "tests" / "data" / "domains" / "testContextInference.ddl"
)
SENSOR_TRACES_DIR = Path(__file__).resolve().parents[2] / "tests" / "data" / "sensorTraces"
_RUN_SECONDS = 5.0


def main() -> None:
    origin = int(time.time() * 1000)
    planner = SimplePlanner(origin, origin + 100000, 0)
    ProactivePlanningDomain.parse_domain(planner, str(DOMAIN_FILE), ProactivePlanningDomain)

    ans = cast(ActivityNetworkSolver, planner.constraint_solvers[0])
    cb = SimplePlannerInferenceCallback(planner)
    animator = ConstraintNetworkAnimator(ans, 1000, cb)

    sensor_a = Sensor("Location", animator)
    sensor_b = Sensor("Stove", animator)
    sensor_a.register_sensor_trace(str(SENSOR_TRACES_DIR / "location.st"), origin)
    sensor_b.register_sensor_trace(str(SENSOR_TRACES_DIR / "stove.st"), origin)

    try:
        server = serve(ans, ["Time", "Location", "Stove", "Human", "RFIDReader"])
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
