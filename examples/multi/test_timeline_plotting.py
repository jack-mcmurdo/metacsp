"""Port of examples/multi/TestTimelinePlotting.java.

The Java original visualizes a live ``TimelineVisualizer`` (Swing) while
looping 200 times, each iteration replacing a ``Release`` constraint and
re-publishing the timeline image; replaced here by M21's
``metacsp.viz.timeline.TimelineWindow`` (dearpygui), refreshed once per
iteration. Iteration count is reduced from 200 to 20 (same 500ms step) so
the demo finishes in ~10s instead of ~100s -- the exact count isn't
semantically meaningful (it just keeps sliding the release window), so this
is a demo-runtime consideration, not a behavior change.
"""

from __future__ import annotations

import time

from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.time.bounds import Bounds
from metacsp.viz.app import VizApp
from metacsp.viz.timeline import TimelineWindow

_ITERATIONS = 20
_STEP_SECONDS = 0.5


def main() -> None:
    time_now = int(time.time() * 1000)
    solver = ActivityNetworkSolver(time_now, time_now + 1000, ["A", "B", "C", "D"])
    act1 = solver.create_variable("One Component")
    assert isinstance(act1, SymbolicVariableActivity)
    act1.set_symbolic_domain("A", "B", "C")
    act2 = solver.create_variable("Another Component")
    assert isinstance(act2, SymbolicVariableActivity)
    act2.set_symbolic_domain("B", "C")

    con1 = SymbolicValueConstraint(SymbolicValueConstraint.Type.EQUALS)
    con1.set_from(act1)
    con1.set_to(act2)

    dur1 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Duration, Bounds(10, 20))
    dur1.from_ = act1
    dur1.to = act1

    dur2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Duration, Bounds(10, 20))
    dur2.from_ = act2
    dur2.to = act2

    con2 = AllenIntervalConstraint(AllenIntervalConstraint.Type.Before, Bounds(10, 20))
    con2.from_ = act1
    con2.to = act2

    solver.add_constraints(dur1, dur2, con1, con2)

    app = VizApp(title="TestTimelinePlotting")
    window = TimelineWindow(solver.constraint_network, ["One Component", "Another Component"])
    app.create()
    window.build(app)
    try:
        con3: AllenIntervalConstraint | None = None
        for i in range(_ITERATIONS):
            time.sleep(_STEP_SECONDS)
            if con3 is not None:
                solver.remove_constraint(con3)
            con3 = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Release,
                Bounds(solver.origin + 7 + i, solver.origin + 10 + i),
            )
            con3.from_ = act1
            con3.to = act1
            solver.add_constraint(con3)
            window.refresh()
    finally:
        window.destroy()
        app.destroy()


if __name__ == "__main__":
    main()
