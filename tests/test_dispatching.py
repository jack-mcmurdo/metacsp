"""Tests for sensing/ + dispatching/ (M19).

There is no ported JUnit test class for these packages (the Java `tests/`
directory has none, and PLAN.md's own M19 description explicitly does not
ask for one); PLAN.md's acceptance criterion is a from-scratch pytest
scenario: an ActivityNetworkSolver + Dispatcher, run with a short period,
asserting activities are dispatched and finished in precedence order.

A ConstraintNetworkAnimator is used alongside the Dispatcher because the
Dispatcher can only ever promote an activity from PLANNED to STARTED once
the network's "Future" activity -- created and advanced only by the
animator -- has moved past that activity's earliest-start time; this is
the realistic (and only) way to drive a Dispatcher, matching how
sensing/ConstraintNetworkAnimator.java and dispatching/Dispatcher.java are
used together in the Java examples this milestone intentionally does not
port (TestProactivePlanningAndDispatching.java et al., left for M22/M20).

The test polls with a timeout (`time.monotonic()`-based deadline) rather
than sleeping a fixed amount and asserting -- required by PLAN.md's M19
acceptance criterion ("dispatch test green and deterministic") -- so it
is robust to real-world thread-scheduling jitter.
"""

from __future__ import annotations

import time

import pytest

from metacsp.dispatching.dispatcher import Dispatcher
from metacsp.dispatching.dispatching_function import DispatchingFunction
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator
from metacsp.time.bounds import Bounds

COMPONENT = "task"
SYMBOLS = ["A", "B", "C"]
# Milliseconds after the animator's origin at which each activity becomes
# eligible for dispatch (its earliest-start time) -- comfortably spaced
# relative to the animator/dispatcher periods below.
ESTS = [150, 400, 650]
PERIOD_MS = 50
POLL_INTERVAL_S = 0.05
POLL_DEADLINE_S = 10.0


class _RecordingDispatchingFunction(DispatchingFunction):
    """Records dispatch order and immediately requests each activity be
    finished (simulating instantaneous execution), so the Dispatcher's
    PLANNED -> STARTED -> FINISHING -> FINISHED lifecycle completes without
    any external actor."""

    def __init__(self, component: str, dispatched: list[str]) -> None:
        super().__init__(component)
        self._dispatched = dispatched

    def dispatch(self, act: SymbolicVariableActivity) -> None:
        self._dispatched.append(act.symbolic_variable.symbols[0])
        self.finish(act)

    def skip(self, act: SymbolicVariableActivity) -> bool:
        return False


def _make_activity(ans: ActivityNetworkSolver, symbol: str, est: int) -> SymbolicVariableActivity:
    act = ans.create_variable(COMPONENT)
    assert isinstance(act, SymbolicVariableActivity)
    act.set_symbolic_domain(symbol)
    act.marking = SimpleDomain.markings.JUSTIFIED
    release = AllenIntervalConstraint(AllenIntervalConstraint.Type.Release, Bounds(est, est))
    release.from_ = act
    release.to = act
    assert ans.add_constraint(release)
    return act


def _finalize_symbolic_domains(ans: ActivityNetworkSolver) -> None:
    """Resolve every activity's ``set_symbolic_domain(...)`` call to a
    single concrete symbol.

    ``set_symbolic_domain`` (both here and in the Java source it ports,
    ``SymbolicVariable.setDomain(String...)``) deliberately adds its
    restricting unary constraint via ``addConstraintNoPropagation`` so many
    activities' domains can be batch-resolved by a single SAT solve rather
    than one per activity. In the full system that solve is triggered as a
    side effect of a planner's own constraint additions (see M19's
    docstring on why this milestone's test does not port
    ``TestProactivePlanningAndDispatching.java`` et al., which depend on
    such a planner); standalone here, it must be triggered explicitly.
    """
    ans.constraint_solvers[1].constraint_solvers[0].propagate()


def test_dispatch_and_finish_in_precedence_order() -> None:
    horizon = 1_000_000
    ans = ActivityNetworkSolver(0, horizon, [*SYMBOLS, "Future"])

    # The animator creates and periodically advances the network's "Future"
    # activity; the Dispatcher (constructed after it) discovers that
    # activity by its "Future" symbol.
    animator = ConstraintNetworkAnimator(ans, PERIOD_MS)

    acts = [_make_activity(ans, symbol, est) for symbol, est in zip(SYMBOLS, ESTS)]
    _finalize_symbolic_domains(ans)

    dispatched: list[str] = []
    dispatcher = Dispatcher(ans, PERIOD_MS)
    dispatcher.add_dispatching_function(
        COMPONENT, _RecordingDispatchingFunction(COMPONENT, dispatched)
    )
    dispatcher.start()

    finished_seen: set[str] = set()
    finished_order: list[str] = []
    deadline = time.monotonic() + POLL_DEADLINE_S
    try:
        while len(finished_seen) < len(SYMBOLS) and time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_S)
            for finished_act in dispatcher.get_finished_acts():
                symbol = finished_act.symbolic_variable.symbols[0]
                if symbol not in finished_seen:
                    finished_seen.add(symbol)
                    finished_order.append(symbol)
    finally:
        dispatcher.teardown()
        animator.teardown()

    if len(finished_seen) < len(SYMBOLS):
        pytest.fail(
            f"timed out after {POLL_DEADLINE_S}s waiting for all activities to finish; "
            f"dispatched={dispatched!r} finished={finished_order!r}"
        )

    assert dispatched == SYMBOLS, "activities must be dispatched in earliest-start-time order"
    assert finished_order == SYMBOLS, "activities must finish in earliest-start-time order"
    assert {act.symbolic_variable.symbols[0] for act in acts} == set(SYMBOLS)
