"""Live demo for `metacsp.viz`: two robots each work through a queue of
tasks, one at a time, driven by a background thread -- `serve()` opens a
browser tab showing the Gantt timeline update live as each task starts.

Run with `pip install metacsp[viz]` installed and a built frontend
(`npm --prefix frontend run build`, or just use a release wheel), then:

    python examples/viz_timeline_demo.py
"""

from __future__ import annotations

import random
import threading
import time

from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.bounds import Bounds
from metacsp.viz import serve

COMPONENTS = ["Robot1", "Robot2"]
TASKS = {
    "Robot1": ["goto_dock", "pick", "goto_shelf", "place", "goto_dock"],
    "Robot2": ["goto_charge", "charge", "goto_shelf", "pick", "goto_delivery"],
}


def _drive(solver: ActivityNetworkSolver, stop: threading.Event) -> None:
    cursor = {c: solver.origin for c in COMPONENTS}
    while not stop.is_set():
        for component in COMPONENTS:
            symbol = random.choice(TASKS[component])
            duration = random.randint(2000, 6000)
            est = cursor[component]

            act = solver.create_variable(component)
            act.set_symbolic_domain(symbol)
            release = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Release, Bounds(est, est)
            )
            release.from_ = act
            release.to = act
            dur = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Duration, Bounds(duration, duration)
            )
            dur.from_ = act
            dur.to = act
            solver.add_constraints(release, dur)

            cursor[component] = est + duration
        time.sleep(1.5)


def main() -> None:
    origin = int(time.time() * 1000)
    solver = ActivityNetworkSolver(origin, origin + 10_000_000)

    stop = threading.Event()
    driver = threading.Thread(target=_drive, args=(solver, stop), daemon=True)
    driver.start()

    server = serve(solver, COMPONENTS)
    print(f"Serving at http://{server.host}:{server.port}/ -- Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.stop()


if __name__ == "__main__":
    main()
