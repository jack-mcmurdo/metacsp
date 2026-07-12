"""Port of dispatching/SimpleDispatchingExampleManualSpecification.java from
the meta-csp-tutorial repo (M23).

The Java original also opens a ``TimelinePublisher``/``TimelineVisualizer``
(Swing); replaced here by M21's ``metacsp.viz.timeline.TimelineWindow``
(dearpygui). The "poor man's key listener" ``while True`` stdin loop is
preserved as-is (meant to be run and typed into by a newcomer); ``input()``
raises ``EOFError`` on closed stdin (where Java's ``BufferedReader
.readLine()`` would return ``null``), caught here to exit cleanly instead
of raising.
"""

from __future__ import annotations

import time

from metacsp.dispatching.dispatching_function import DispatchingFunction
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.viz.app import VizApp
from metacsp.viz.timeline import TimelineWindow


class _PrintingDispatchingFunction(DispatchingFunction):
    def skip(self, act: SymbolicVariableActivity) -> bool:
        return False

    def dispatch(self, act: SymbolicVariableActivity) -> None:
        print(f"{act.component} starts executing {act.symbols[0]}")


def main() -> None:
    origin = int(time.time() * 1000)

    # Create ActivityNetworkSolver, origin = current time.
    ans = ActivityNetworkSolver(origin, origin + 100000)

    # Here is the example...
    #                     Delivery location
    #                             x
    #                             ^
    #                             |
    #                             |
    #                             |
    # MiR location                |
    #      x -------------------> x
    #                       UR location
    #
    # Let's construct the example manually...
    # We make one variable for each meaningful activity.
    goto_ur = ans.create_variable("MiR")
    assert isinstance(goto_ur, SymbolicVariableActivity)
    goto_ur.set_symbolic_domain("goto_ur")
    goto_delivery = ans.create_variable("MiR")
    assert isinstance(goto_delivery, SymbolicVariableActivity)
    goto_delivery.set_symbolic_domain("goto_delivery")
    place_obj = ans.create_variable("UR")
    assert isinstance(place_obj, SymbolicVariableActivity)
    place_obj.set_symbolic_domain("place_obj")

    # Set the minimum durations of activities (at least 3 seconds for all
    # activities, just as an example).
    goto_ur_min_duration = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Duration, Bounds(3000, APSPSolver.INF)
    )
    goto_ur_min_duration.from_ = goto_ur
    goto_ur_min_duration.to = goto_ur

    goto_delivery_min_duration = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Duration, Bounds(3000, APSPSolver.INF)
    )
    goto_delivery_min_duration.from_ = goto_delivery
    goto_delivery_min_duration.to = goto_delivery

    place_obj_min_duration = AllenIntervalConstraint(
        AllenIntervalConstraint.Type.Duration, Bounds(3000, APSPSolver.INF)
    )
    place_obj_min_duration.from_ = place_obj
    place_obj_min_duration.to = place_obj

    # Add the desired temporal relations between activities: MiR has to be
    # finished with goto_ur before UR starts place_obj...
    goto_meets_place = AllenIntervalConstraint(AllenIntervalConstraint.Type.Before)
    goto_meets_place.from_ = goto_ur
    goto_meets_place.to = place_obj

    # ...and UR has to have finished place_obj before MiR can start goto_delivery.
    place_before_goto = AllenIntervalConstraint(AllenIntervalConstraint.Type.Before)
    place_before_goto.from_ = place_obj
    place_before_goto.to = goto_delivery

    # Now we add the specified constraints to the solver...
    added = ans.add_constraints(
        goto_ur_min_duration,
        goto_delivery_min_duration,
        place_obj_min_duration,
        goto_meets_place,
        place_before_goto,
    )
    # ...which checks for consistency.
    print("Constraints consistent?", added)

    # Now let's make this come alive!

    # Create animator and tell it to animate the ActivityNetworkSolver w/ period 100 msec.
    animator = ConstraintNetworkAnimator(ans, 100)

    df_mir = _PrintingDispatchingFunction("MiR")
    df_ur = _PrintingDispatchingFunction("UR")
    animator.add_dispatching_functions(df_mir, df_ur)

    # Visualize progression, with automatic update every 100 msec.
    app = VizApp(title="SimpleDispatchingExampleManualSpecification")
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
