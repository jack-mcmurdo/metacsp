"""Port of sensing/ConstraintNetworkAnimator.java."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Callable, cast

from metacsp.dispatching.dispatcher import Dispatcher, _solver_lock
from metacsp.dispatching.dispatching_function import DispatchingFunction
from metacsp.exceptions import NetworkMaintenanceError
from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.meta.fuzzy_activity.fuzzy_activity_domain import FuzzyActivityDomain
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.sensing.controllable import Controllable
from metacsp.time.bounds import Bounds
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.variable import Variable
    from metacsp.sensing.sensor import Sensor

__all__ = ["ConstraintNetworkAnimator", "InferenceCallback", "PeriodicCallback"]

#: Java ``InferenceCallback`` (single-method interface, C4): any callable
#: ``(time_now: int) -> None``, invoked once per un-paused animator tick
#: (e.g. to trigger a planner run).
InferenceCallback = Callable[[int], None]

#: Java ``PeriodicCallback`` (single-method interface, C4): any callable
#: ``(time_now: int) -> None``, invoked once per un-paused animator tick,
#: after the InferenceCallback.
PeriodicCallback = Callable[[int], None]


class ConstraintNetworkAnimator:
    """Drives a "Future" activity forward in wall-clock time (one tick every
    ``period`` ms) so that a :class:`~metacsp.dispatching.dispatcher
    .Dispatcher` has something to compare activities' earliest-start times
    against, and optionally animates registered
    :class:`~metacsp.sensing.sensor.Sensor` traces and calls a planner
    (:data:`InferenceCallback`) and/or extra periodic hooks
    (:data:`PeriodicCallback`) on every tick.

    Follows D9: the Java ``while(true) { sleep(period); ... }`` loop
    (inherited from ``Thread.run()``) runs on a daemon
    :class:`threading.Thread`, started automatically by the constructor
    (matching Java, whose constructor calls ``this.start()``); call
    :meth:`teardown` to stop it.
    """

    def __init__(
        self,
        ans: ActivityNetworkSolver,
        period: int,
        inference_callback_or_start_paused: InferenceCallback | bool | None = None,
        start_paused: bool = False,
    ) -> None:
        # Collapses Java's 4 constructor overloads: (ans, period),
        # (ans, period, startPaused), (ans, period, cb),
        # (ans, period, cb, startPaused).
        cb: InferenceCallback | None
        if isinstance(inference_callback_or_start_paused, bool):
            cb = None
            start_paused = inference_callback_or_start_paused
        else:
            cb = inference_callback_or_start_paused

        self._cb = cb
        self._pcbs: list[PeriodicCallback] | None = None
        self._dis: Dispatcher | None = None
        self._paused = start_paused
        self._teardown = False
        self._auto_clean = False
        self._sensor_values: dict[Sensor, dict[int, str]] = {}
        self._controllable_values: dict[Controllable, dict[int, str]] = {}
        self.logger = get_logger(type(self))

        with _solver_lock(ans):
            self.ans = ans
            self.period = period
            self._origin_of_time = ans.origin
            self._first_tick = self._get_current_time_in_millis()
            self.cn = ans.constraint_network
            future = cast(SymbolicVariableActivity, ans.create_variable("Time"))
            future.set_symbolic_domain("Future")
            future.marking = FuzzyActivityDomain.markings.JUSTIFIED
            self._future = future
            time_now = self.time_now
            release_future = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Release, Bounds(time_now, time_now)
            )
            release_future.from_ = future
            release_future.to = future
            deadline_future = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Deadline, Bounds(ans.horizon, ans.horizon)
            )
            deadline_future.from_ = future
            deadline_future.to = future
            self._current_release_future: AllenIntervalConstraint | None = release_future
            if not ans.add_constraints(self._current_release_future, deadline_future):
                raise NetworkMaintenanceError(self._current_release_future, deadline_future)

            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def add_periodic_callbacks(self, *callbacks: PeriodicCallback) -> None:
        """Register callables invoked once per un-paused tick, after the InferenceCallback."""
        if self._pcbs is None:
            self._pcbs = []
        self._pcbs.extend(callbacks)

    def _get_current_time_in_millis(self) -> int:
        return time.time_ns() // 1_000_000

    def set_inference_callback(self, cb: InferenceCallback) -> None:
        """Set the callable invoked once per un-paused tick (e.g. to trigger a planner run)."""
        self._cb = cb

    def set_auto_clean_finished_variables(self, ac: bool) -> None:
        """Set whether finished activities' variables are automatically removed."""
        self._auto_clean = ac

    def is_unknown(self, act: SymbolicVariableActivity) -> bool:
        """True iff the Dispatcher does not know about the given activity."""
        assert self._dis is not None
        return any(activity == act for activity in self._dis.get_activities())

    def is_in_state(self, act: SymbolicVariableActivity, st: Dispatcher.ACTIVITY_STATE) -> bool:
        """True iff the given activity is currently in the given dispatching state."""
        assert self._dis is not None
        return any(dis_act == act for dis_act in self._dis.get_acts_in_state(st))

    def is_started(self, act: SymbolicVariableActivity) -> bool:
        """True iff the given activity has been dispatched (started)."""
        assert self._dis is not None
        return any(started_act == act for started_act in self._dis.get_started_acts())

    def is_finished(self, act: SymbolicVariableActivity) -> bool:
        """True iff the given activity has finished dispatching."""
        assert self._dis is not None
        return any(finished_act == act for finished_act in self._dis.get_finished_acts())

    def _clean_up(self) -> None:
        assert self._dis is not None
        finished_acts = self._dis.get_finished_acts()
        for finished_act in finished_acts:
            finished_var: Variable = finished_act.root_variable
            var_solver = finished_var.constraint_solver

            if (
                var_solver.constraint_network.contains_variable(finished_var)
                and not finished_var.is_dependent_variable
            ):
                count_cons = 0

                cons_to_remove = (
                    var_solver.constraint_network.get_incident_edges_including_dependent_variables(
                        finished_var
                    )
                )
                var_solver.remove_constraints(cons_to_remove)
                count_cons += len(cons_to_remove)

                dep_vars = finished_var.recursively_dependent_variables
                for dep_var in dep_vars:
                    dep_var_solver = dep_var.constraint_solver
                    cons_to_remove_dep_vars = dep_var_solver.constraint_network.get_incident_edges(
                        dep_var
                    )
                    dep_var_solver.remove_constraints(cons_to_remove_dep_vars)
                    count_cons += len(cons_to_remove_dep_vars)

                    dep_act = cast(
                        SymbolicVariableActivity,
                        cast(MultiVariable, dep_var).get_variables_from_variable_hierarchy(
                            SymbolicVariableActivity
                        )[0],
                    )
                    cons_to_remove_dep_act = self.ans.constraint_network.get_incident_edges(dep_act)
                    self.ans.remove_constraints(cons_to_remove_dep_act)
                    count_cons += len(cons_to_remove_dep_act)

                    self._dis.remove_finished_variable(dep_act)

                self._dis.remove_finished_variable(finished_act)

                self.logger.info(
                    "Cleaned up %d variables and %d constraints", len(dep_vars), count_cons
                )

                var_solver.remove_variable(finished_var)

    @property
    def constraint_network(self) -> ConstraintNetwork:
        """The ConstraintNetwork of this animator's ActivityNetworkSolver."""
        return self.cn

    @property
    def activity_network_solver(self) -> ActivityNetworkSolver:
        """The ActivityNetworkSolver this animator drives."""
        return self.ans

    def post_sensor_value_to_dispatch(self, sensor: Sensor, time: int, value: str) -> None:
        """Queue a single sensor reading to be applied on a future tick."""
        with _solver_lock(self.ans):
            self._sensor_values.setdefault(sensor, {})[time] = value

    def post_controllable_value_to_dispatch(
        self, controllable: Controllable, time: int, value: str
    ) -> None:
        """Queue a single controllable-component value to be applied on a future tick."""
        with _solver_lock(self.ans):
            self._controllable_values.setdefault(controllable, {})[time] = value

    def register_sensor_values_to_dispatch(self, sensor: Sensor, values: dict[int, str]) -> None:
        """Replace the full queue of pending readings for a sensor."""
        self._sensor_values[sensor] = values

    def register_controllable_values_to_dispatch(
        self, controllable: Controllable, values: dict[int, str]
    ) -> None:
        """Replace the full queue of pending values for a controllable component."""
        self._controllable_values[controllable] = values

    def add_dispatching_functions(
        self, *dfs: DispatchingFunction, ans: ActivityNetworkSolver | None = None
    ) -> None:
        """Register dispatching functions, creating (and starting) this
        animator's :class:`Dispatcher` on first call.

        ``ans``, if given, corresponds to Java's ``@Deprecated
        addDispatchingFunctions(ActivityNetworkSolver, DispatchingFunction
        ...)`` overload (use a different solver than this animator's own);
        omitted, this animator's own solver is used -- the non-deprecated
        overload's behavior, and (since callers always pass this animator's
        own solver in practice) observably identical to the deprecated one.
        """
        solver = ans if ans is not None else self.ans
        start = False
        if self._dis is None:
            self._dis = Dispatcher(solver, self.period)
            start = True
        for df in dfs:
            self._dis.add_dispatching_function(df.component, df)
        if start:
            self._dis.start()

    @property
    def time_now(self) -> int:
        """The current time, mapped into this animator's STP's time frame."""
        return self._get_current_time_in_millis() - self._first_tick + self._origin_of_time

    def set_paused(self, paused: bool) -> None:
        """Pause or resume ticking (sensor animation, callbacks, and Future's advance)."""
        self._paused = paused

    def teardown(self) -> None:
        """Stop this animator's background thread (and its Dispatcher, if any)."""
        self._teardown = True

    def _run(self) -> None:
        iteration = 0
        while not self._teardown:
            time.sleep(self.period / 1000.0)

            if not self._paused:
                with _solver_lock(self.ans):
                    # Update release constraint of Future
                    time_now = self.time_now
                    release_future = AllenIntervalConstraint(
                        AllenIntervalConstraint.Type.Release, Bounds(time_now, time_now)
                    )
                    release_future.from_ = self._future
                    release_future.to = self._future
                    if self._current_release_future is not None:
                        self.ans.remove_constraint(self._current_release_future)
                    if not self.ans.add_constraint(release_future):
                        self.logger.warning(
                            "Could not release Future: incident edges %s",
                            self.ans.constraint_network.get_incident_edges(self._future),
                        )
                        raise NetworkMaintenanceError(release_future)
                    self._current_release_future = release_future

                    # If there are registered sensor traces, animate them too
                    for sensor, values in list(self._sensor_values.items()):
                        to_remove: list[int] = []
                        for t in sorted(values.keys()):
                            if t <= time_now:
                                sensor.model_sensor_value(values[t], t)
                                to_remove.append(t)
                        for t in to_remove:
                            del values[t]

                    # If there is a registered InferenceCallback (e.g., call a planner), run it
                    if self._cb is not None:
                        self._cb(time_now)

                    if self._pcbs is not None:
                        for pc in self._pcbs:
                            pc(time_now)

                    # Remove finished vars
                    if self._auto_clean:
                        finished_vars = len(self._dis.get_finished_acts()) if self._dis else 0
                        if finished_vars > 0:
                            self._clean_up()

                    # Print iteration number
                    self.logger.info("Iteration %d @%d", iteration, time_now)
                    iteration += 1
        if self._dis is not None:
            self._dis.teardown()
        self.logger.info("Shut down")

    @property
    def dispatcher(self) -> Dispatcher | None:
        """This animator's Dispatcher, once created by :meth:`add_dispatching_functions`."""
        return self._dis
