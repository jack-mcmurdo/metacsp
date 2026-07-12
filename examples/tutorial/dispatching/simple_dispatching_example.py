"""Port of dispatching/SimpleDispatchingExample.java from the
meta-csp-tutorial repo (M23).

The Java original also opens a ``TimelinePublisher``/``TimelineVisualizer``
(Swing); replaced here by M21's ``metacsp.viz.timeline.TimelineWindow``
(dearpygui). The "poor man's key listener" ``while True`` stdin loop is
preserved as-is (meant to be run and typed into by a newcomer); ``input()``
raises ``EOFError`` on closed stdin (where Java's ``BufferedReader
.readLine()`` would return ``null``), caught here to exit cleanly instead
of raising.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metacsp.dispatching.dispatching_function import DispatchingFunction
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.viz.app import VizApp
from metacsp.viz.timeline import TimelineWindow
from util import parsing

_SPECIFICATION_FILE = Path(__file__).resolve().parent / "specification.txt"


class _PrintingDispatchingFunction(DispatchingFunction):
    def skip(self, act: SymbolicVariableActivity) -> bool:
        return False

    def dispatch(self, act: SymbolicVariableActivity) -> None:
        print(f"{act.component} starts executing {act.symbols[0]}")


def main() -> None:
    origin = int(time.time() * 1000)

    # Create ActivityNetworkSolver, origin = current time.
    ans = ActivityNetworkSolver(origin, origin + 1000000)

    # Parse the specification...
    parsing.set_variable_factory(ans)
    cn = parsing.load_specification(str(_SPECIFICATION_FILE))
    # ... and add the parsed constraints.
    added = ans.add_constraints(*cn.get_constraints())
    print("Constraints consistent?", added)

    # Now let's make this come alive!

    # Create animator and tell it to animate the ActivityNetworkSolver w/ period 100 msec.
    animator = ConstraintNetworkAnimator(ans, 100)

    df_mir = _PrintingDispatchingFunction("MiR")
    df_ur = _PrintingDispatchingFunction("UR")
    animator.add_dispatching_functions(df_mir, df_ur)

    # Visualize progression, with automatic update every 100 msec.
    app = VizApp(title="SimpleDispatchingExample")
    window = TimelineWindow(ans.constraint_network, ["MiR", "UR"])
    app.create()
    window.build(app)
    window.attach()

    try:
        while True:
            print("Executing activities (press <enter> to refresh list):")
            acts = animator.dispatcher.get_started_acts() if animator.dispatcher else []
            for i, act in enumerate(acts):
                print(f"{i}: {act}")
            print("--")
            try:
                choice = input("Please enter activity to finish: ")
            except EOFError:
                break
            choice = choice.strip()
            if choice:
                try:
                    act_to_finish = acts[int(choice)]
                    df = animator.dispatcher.get_dispatching_function(act_to_finish.component)
                    assert df is not None
                    df.finish(act_to_finish)
                    print(
                        f"{act_to_finish.component} finishes executing {act_to_finish.symbols[0]}"
                    )
                except (ValueError, IndexError):
                    pass
    finally:
        window.destroy()
        app.destroy()
        animator.teardown()


if __name__ == "__main__":
    main()
