"""Port of dispatching/Dispatcher.java."""

from __future__ import annotations

import threading
import time
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, cast

from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.bounds import Bounds
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.dispatching.dispatching_function import DispatchingFunction
    from metacsp.framework.constraint_network import ConstraintNetwork

__all__ = ["Dispatcher"]


def _solver_lock(solver: Any) -> threading.RLock:
    """Return (creating if absent) a lock attached to *solver*.

    Mirrors Java's ``synchronized(ans)`` critical sections, which are shared
    across every :class:`Dispatcher`, :class:`~metacsp.sensing.sensor.Sensor`
    and :class:`~metacsp.sensing.constraint_network_animator
    .ConstraintNetworkAnimator` instance wrapping the same
    ActivityNetworkSolver -- Python has no built-in per-object monitor, so
    the lock is lazily attached to the solver instance itself.
    """
    lock = getattr(solver, "_metacsp_sync_lock", None)
    if lock is None:
        lock = threading.RLock()
        solver._metacsp_sync_lock = lock
    return cast(threading.RLock, lock)


class Dispatcher:
    """Periodically (every ``period`` ms) dispatches PLANNED activities of
    each registered component whose earliest-start time has come, by
    overlapping them with the network's "Future" activity (created by a
    :class:`~metacsp.sensing.constraint_network_animator
    .ConstraintNetworkAnimator`) and invoking that component's
    :class:`~metacsp.dispatching.dispatching_function.DispatchingFunction`.

    Follows D9: the Java ``while(true) { sleep(period); ... }`` loop
    (inherited from ``Thread.run()``) runs on a daemon
    :class:`threading.Thread`; call :meth:`start` to launch it (matching
    Java's ``Thread.start()``, not called automatically by the constructor)
    and :meth:`teardown` to stop it.
    """

    class ACTIVITY_STATE(Enum):
        """The lifecycle states of an activity as tracked by the Dispatcher."""

        PLANNED = auto()
        STARTED = auto()
        FINISHING = auto()
        MANUALLY_FINISHING = auto()
        FINISHED = auto()
        SKIP_BECAUSE_UNIFICATION = auto()
        MANUALLY_STARTED = auto()

    def __init__(self, ans: ActivityNetworkSolver, period: int) -> None:
        self.ans = ans
        self.cn = ans.constraint_network
        self.period = period
        self.acts: dict[SymbolicVariableActivity, Dispatcher.ACTIVITY_STATE] = {}
        self.overlap_future_constraints: dict[SymbolicVariableActivity, AllenIntervalConstraint] = (
            {}
        )
        self.dfs: dict[str, DispatchingFunction] = {}
        self.future: SymbolicVariableActivity | None = None
        for var in self.cn.get_variables():
            if isinstance(var, SymbolicVariableActivity):
                candidate_future = var
                symbols = candidate_future.symbolic_variable.symbols
                if len(symbols) > 0 and symbols[0] == "Future":
                    self.future = candidate_future
                    break
        self.logger = get_logger(type(self))
        self._teardown = False
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Start the dispatch thread (Java ``Thread.start()``)."""
        self._thread.start()

    def teardown(self) -> None:
        self._teardown = True

    def remove_finished_variable(self, to_remove: SymbolicVariableActivity) -> None:
        self.acts.pop(to_remove, None)

    def _equivalent_activities(
        self, act1: SymbolicVariableActivity, act2: SymbolicVariableActivity
    ) -> bool:
        if act1.component != act2.component:
            return False
        if act1.symbolic_variable.symbols[0] != act2.symbolic_variable.symbols[0]:
            return False
        if act1.temporal_variable.est != act2.temporal_variable.est:
            return False
        if act1.temporal_variable.eet != act2.temporal_variable.eet:
            return False
        return True

    def manual_start(self, act: SymbolicVariableActivity, component: str) -> None:
        self.acts[act] = Dispatcher.ACTIVITY_STATE.MANUALLY_STARTED

    def _run(self) -> None:
        while not self._teardown:
            time.sleep(self.period / 1000.0)
            with _solver_lock(self.ans):
                for component in list(self.dfs.keys()):
                    current_vars = [
                        v
                        for v in self.cn.get_variables(component)
                        if isinstance(v, SymbolicVariableActivity)
                    ]
                    current_vars.sort()
                    for act in current_vars:
                        if self.dfs[component].skip(act):
                            continue

                        if act not in self.acts:
                            skip = False
                            outgoing = self.ans.constraint_network.get_outgoing_edges(act)
                            for con in outgoing:
                                if isinstance(con, AllenIntervalConstraint):
                                    to = cast(SymbolicVariableActivity, con.to)
                                    if (
                                        to.component == act.component
                                        and to.symbolic_variable.symbols[0]
                                        == act.symbolic_variable.symbols[0]
                                        and con.types[0] == AllenIntervalConstraint.Type.Equals
                                    ):
                                        skip = True
                                        self.logger.warning("IGNORED UNIFICATION %s", con)
                                        break
                            self.acts[act] = (
                                Dispatcher.ACTIVITY_STATE.SKIP_BECAUSE_UNIFICATION
                                if skip
                                else Dispatcher.ACTIVITY_STATE.PLANNED
                            )

                        if self.acts[act] == Dispatcher.ACTIVITY_STATE.PLANNED:
                            assert self.future is not None
                            if act.temporal_variable.est < self.future.temporal_variable.est:
                                self.acts[act] = Dispatcher.ACTIVITY_STATE.STARTED
                                overlaps_future = AllenIntervalConstraint(
                                    AllenIntervalConstraint.Type.Overlaps
                                )
                                overlaps_future.from_ = act
                                overlaps_future.to = self.future
                                ret = self.ans.add_constraint(overlaps_future)
                                if not ret:
                                    self.logger.warning(
                                        "IGNORED dispatching (future is at %s):\n\t%s",
                                        self.future.temporal_variable.est,
                                        act,
                                    )
                                    self.logger.warning("Constraints on ignored activity are:")
                                    for c in self.ans.constraint_network.get_incident_edges(act):
                                        self.logger.warning("\t%s", c)
                                    self.logger.warning("%s", current_vars)
                                else:
                                    self.overlap_future_constraints[act] = overlaps_future
                                    self.dfs[component].dispatch(act)

                        elif self.acts[act] == Dispatcher.ACTIVITY_STATE.FINISHING:
                            self.acts[act] = Dispatcher.ACTIVITY_STATE.FINISHED
                            self.ans.remove_constraint(self.overlap_future_constraints.get(act))
                            assert self.future is not None
                            deadline = AllenIntervalConstraint(
                                AllenIntervalConstraint.Type.Deadline,
                                Bounds(
                                    self.future.temporal_variable.est,
                                    self.future.temporal_variable.est,
                                ),
                            )
                            deadline.from_ = act
                            deadline.to = act
                            if not self.ans.add_constraint(deadline):
                                default_deadline = AllenIntervalConstraint(
                                    AllenIntervalConstraint.Type.Deadline,
                                    Bounds(act.temporal_variable.eet, act.temporal_variable.eet),
                                )
                                default_deadline.from_ = act
                                default_deadline.to = act
                                self.ans.add_constraint(default_deadline)

                        elif self.acts[act] == Dispatcher.ACTIVITY_STATE.MANUALLY_FINISHING:
                            self.acts[act] = Dispatcher.ACTIVITY_STATE.FINISHED
        self.logger.info("Shut down")

    def add_dispatching_function(self, component: str, df: DispatchingFunction) -> None:
        df.register_dispatcher(self)
        self.dfs[component] = df

    def get_dispatching_function(self, component: str) -> DispatchingFunction | None:
        return self.dfs.get(component)

    def get_activities(self) -> list[SymbolicVariableActivity]:
        return list(self.acts.keys())

    def get_acts_in_state(self, st: Dispatcher.ACTIVITY_STATE) -> list[SymbolicVariableActivity]:
        return [act for act, state in self.acts.items() if state == st]

    def get_started_acts(self) -> list[SymbolicVariableActivity]:
        return self.get_acts_in_state(Dispatcher.ACTIVITY_STATE.STARTED)

    def get_finished_acts(self) -> list[SymbolicVariableActivity]:
        return self.get_acts_in_state(Dispatcher.ACTIVITY_STATE.FINISHED)

    def finish(self, *acts_to_finish: SymbolicVariableActivity) -> None:
        for act in acts_to_finish:
            self.acts[act] = Dispatcher.ACTIVITY_STATE.FINISHING

    @property
    def constraint_network(self) -> ConstraintNetwork:
        return self.ans.constraint_network
