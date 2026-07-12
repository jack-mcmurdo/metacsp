"""Port of planning/TestProactivePlanningAndDispatching.java from the
meta-csp-tutorial repo (M23).

This tutorial example is byte-for-byte identical (down to the domain and
sensor-trace filenames) to the framework repo's own
``examples/meta/TestProactivePlanningAndDispatching.java``, ported
independently in M22 as
``examples/meta/test_proactive_planning_and_dispatching.py`` -- the two
Python ports are intentionally near-duplicates, one per oracle repo,
matching their (also duplicate) Java sources.

The Java original visualizes progression forever via
``TimelineVisualizer.startAutomaticUpdate`` (Swing) -- replaced here by
M21's ``metacsp.viz.timeline.TimelineWindow`` (dearpygui), attached to
live-redraw on every D2 change event. The "poor man's key listener" `while
True` stdin loop is preserved as-is (meant to be run and typed into by a
newcomer); ``input()`` raises ``EOFError`` on closed stdin (where Java's
``BufferedReader.readLine()`` would return ``null``), caught here to exit
cleanly instead of raising.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from metacsp.dispatching.dispatching_function import DispatchingFunction
from metacsp.meta.simple_planner import ProactivePlanningDomain
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.meta.simple_planner.simple_planner import SimplePlanner
from metacsp.meta.simple_planner.simple_planner_inference_callback import (
    SimplePlannerInferenceCallback,
)
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.sensing.sensor import Sensor
from metacsp.viz.app import VizApp
from metacsp.viz.timeline import TimelineWindow

DOMAIN_FILE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "data"
    / "domains"
    / "testProactivePlanningLucia.ddl"
)
SENSOR_TRACES_DIR = Path(__file__).resolve().parents[3] / "tests" / "data" / "sensorTraces"


class _RobotDispatchingFunction(DispatchingFunction):
    def __init__(self, executing_acts: list[SymbolicVariableActivity]) -> None:
        super().__init__("Robot")
        self._executing_acts = executing_acts

    def dispatch(self, act: SymbolicVariableActivity) -> None:
        print(">>>>>>>>>>>>>> Dispatched", act)
        self._executing_acts.append(act)

    def skip(self, act: SymbolicVariableActivity) -> bool:
        return False


def main() -> None:
    planner = SimplePlanner(0, 100000, 0)
    SimpleDomain.parse_domain(planner, str(DOMAIN_FILE), ProactivePlanningDomain)

    ans = cast(ActivityNetworkSolver, planner.constraint_solvers[0])
    cb = SimplePlannerInferenceCallback(planner)
    animator = ConstraintNetworkAnimator(ans, 1000, cb)

    executing_acts: list[SymbolicVariableActivity] = []
    df = _RobotDispatchingFunction(executing_acts)
    animator.add_dispatching_functions(df)

    sensor_a = Sensor("Location", animator)
    sensor_b = Sensor("Stove", animator)
    sensor_a.register_sensor_trace(str(SENSOR_TRACES_DIR / "location.st"))
    sensor_b.register_sensor_trace(str(SENSOR_TRACES_DIR / "stove.st"))

    app = VizApp(title="TestProactivePlanningAndDispatching (tutorial)")
    window = TimelineWindow(ans.constraint_network, ["Time", "Location", "Stove", "Human", "Robot"])
    app.create()
    window.build(app)
    window.attach()
    try:
        while True:
            print("Executing activities (press <enter> to refresh list):")
            for i, act in enumerate(executing_acts):
                print(f"{i}. {act}")
            print("--")
            try:
                choice = input("Please enter activity to finish: ")
            except EOFError:
                break
            choice = choice.strip()
            if choice:
                try:
                    act_to_finish = executing_acts[int(choice)]
                    df.finish(act_to_finish)
                    executing_acts.remove(act_to_finish)
                except (ValueError, IndexError):
                    pass
    finally:
        window.destroy()
        app.destroy()
        animator.teardown()


if __name__ == "__main__":
    main()
