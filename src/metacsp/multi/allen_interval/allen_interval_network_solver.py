"""Port of multi/allenInterval/AllenIntervalNetworkSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.allen_interval.allen_interval import AllenInterval
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable
    from metacsp.time.bounds import Bounds
    from metacsp.time.time_point import TimePoint

__all__ = ["AllenIntervalNetworkSolver"]


class AllenIntervalNetworkSolver(MultiConstraintSolver):
    """A MultiConstraintSolver over AllenIntervals/AllenIntervalConstraints,
    delegating temporal propagation to a single internal APSPSolver."""

    def __init__(self, origin: int, horizon: int, max_activities: int | None = None) -> None:
        super().__init__(
            [AllenIntervalConstraint],
            AllenInterval,
            self._create_constraint_solvers(origin, horizon, max_activities),
            [2],
        )
        self._activity_network_rollback: list[ConstraintNetwork] = []

    @staticmethod
    def _create_constraint_solvers(
        origin: int, horizon: int, max_activities: int | None
    ) -> list[ConstraintSolver]:
        if max_activities is not None and max_activities >= 1:
            stp_solver = APSPSolver(origin, horizon, 2 * max_activities)
        else:
            stp_solver = APSPSolver(origin, horizon)
        return [stp_solver]

    @property
    def origin(self) -> int:
        return cast(APSPSolver, self.constraint_solvers[0]).o

    @property
    def horizon(self) -> int:
        return cast(APSPSolver, self.constraint_solvers[0]).h

    def get_admissible_distance_bounds(
        self, tp_from: TimePoint, tp_to: TimePoint | None = None
    ) -> Bounds:
        """Bounds of the distance between two TimePoints, or (if ``tp_to`` is
        omitted) between the network's global source and ``tp_from``."""
        stp_solver = cast(APSPSolver, self.constraint_solvers[0])
        if tp_to is None:
            return stp_solver.get_distance_bounds(stp_solver.source, tp_from)
        return stp_solver.get_distance_bounds(tp_from, tp_to)

    @property
    def rigidity_number(self) -> float:
        return cast(APSPSolver, self.constraint_solvers[0]).get_rms_rigidity()

    def propagate(self) -> bool:
        # Do nothing, APSPSolver takes care of propagation.
        return True

    def bookmark(self) -> int:
        a_net = self.constraint_network.clone()
        self._activity_network_rollback.append(a_net)
        stp_solver = cast(APSPSolver, self.constraint_solvers[0])
        return stp_solver.bookmark()

    def remove_bookmark(self, i: int) -> None:
        del self._activity_network_rollback[i]
        stp_solver = cast(APSPSolver, self.constraint_solvers[0])
        stp_solver.remove_bookmark(i)

    def revert(self, i: int) -> None:
        self.the_network = self._activity_network_rollback[i]
        del self._activity_network_rollback[i:]

        stp_solver = cast(APSPSolver, self.constraint_solvers[0])
        stp_solver.revert(i)

        a_net = self.the_network
        for v in a_net.get_variables():
            v_ai = cast(AllenInterval, v)
            v_ai.start = stp_solver.get_equal_time_point(v_ai.start)
            v_ai.end = stp_solver.get_equal_time_point(v_ai.end)

    @property
    def num_bookmarks(self) -> int:
        return cast(APSPSolver, self.constraint_solvers[0]).num_bookmarks
