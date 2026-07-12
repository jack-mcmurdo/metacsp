"""Port of multi/activity/ActivityNetworkSolver.java.

The Gantt-chart drawing methods (``draw_as_gantt*``, Swing
``PlotActivityNetworkGantt``) are not ported -- see D10; M21 will provide a
matplotlib-based timeline plot instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.multi.symbols.symbolic_variable_constraint_solver import (
    SymbolicVariableConstraintSolver,
)

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable

__all__ = ["ActivityNetworkSolver"]


class ActivityNetworkSolver(MultiConstraintSolver):
    """A MultiConstraintSolver over SymbolicVariableActivities: a
    combination of an AllenIntervalNetworkSolver (temporal placement) and a
    SymbolicVariableConstraintSolver (symbolic value)."""

    MAX_ACTIVITIES: ClassVar[int] = 500

    def __init__(
        self,
        origin: int,
        horizon: int,
        num_activities_or_symbols: int | list[str] | None = None,
        symbols: list[str] | None = None,
    ) -> None:
        num_activities: int | None
        if isinstance(num_activities_or_symbols, list):
            symbols = num_activities_or_symbols
            num_activities = None
        else:
            num_activities = num_activities_or_symbols

        if symbols is None and num_activities is None:
            solvers = self._create_constraint_solvers(origin, horizon, 500)
        elif symbols is None:
            assert num_activities is not None
            solvers = self._create_constraint_solvers(origin, horizon, num_activities)
            ActivityNetworkSolver.MAX_ACTIVITIES = num_activities
        elif num_activities is None:
            solvers = self._create_constraint_solvers_with_symbols(
                origin, horizon, ActivityNetworkSolver.MAX_ACTIVITIES, symbols
            )
        else:
            solvers = self._create_constraint_solvers_with_symbols(
                origin, horizon, num_activities, symbols
            )
            ActivityNetworkSolver.MAX_ACTIVITIES = num_activities

        super().__init__(
            [AllenIntervalConstraint, SymbolicValueConstraint],
            SymbolicVariableActivity,
            solvers,
            [1, 1],
        )
        self.ids = 0
        self.origin = origin
        self.horizon = horizon

    @staticmethod
    def _create_constraint_solvers(
        origin: int, horizon: int, num_activities: int
    ) -> list[ConstraintSolver]:
        return [
            AllenIntervalNetworkSolver(origin, horizon, num_activities),
            SymbolicVariableConstraintSolver(),
        ]

    @staticmethod
    def _create_constraint_solvers_with_symbols(
        origin: int, horizon: int, num_activities: int, symbols: list[str]
    ) -> list[ConstraintSolver]:
        return [
            AllenIntervalNetworkSolver(origin, horizon, num_activities),
            SymbolicVariableConstraintSolver(symbols, num_activities),
        ]

    @property
    def rigidity_number(self) -> float:
        """The rigidity number of the underlying APSPSolver's ConstraintNetwork."""
        return cast(AllenIntervalNetworkSolver, self.constraint_solvers[0]).rigidity_number

    def get_allen_interval_network_solver(self) -> AllenIntervalNetworkSolver:
        """This solver's internal AllenIntervalNetworkSolver (temporal-placement layer)."""
        return cast(AllenIntervalNetworkSolver, self.constraint_solvers[0])

    def draw_as_gantt(self, selected_variable_names: list[str] | None = None) -> None:
        """Draw all (or selected) activities on a Gantt chart.

        The Java Swing ``PlotActivityNetworkGantt`` viewer is not ported
        (skip list); a matplotlib-based timeline plot is planned for M21.
        """
        raise NotImplementedError("the Swing Gantt chart viewer is not ported; see D10, M21")

    def propagate(self) -> bool:
        """No-op: propagation is delegated entirely to the internal solvers."""
        # For now, does nothing. Propagation is taken care of by lower layers
        # (ultimately, the underlying temporal constraints are propagated by APSPSolver).
        return True

    def bookmark(self) -> int:
        """Snapshot the underlying AllenIntervalNetworkSolver; return the bookmark's index."""
        a_solver = cast(AllenIntervalNetworkSolver, self.constraint_solvers[0])
        return a_solver.bookmark()

    def remove_bookmarks(self, i: int) -> None:
        """Discard the bookmark at the given index without reverting to it."""
        a_solver = cast(AllenIntervalNetworkSolver, self.constraint_solvers[0])
        a_solver.remove_bookmark(i)

    def revert(self, i: int) -> None:
        """Restore the state saved by :meth:`bookmark` at index ``i``, discarding later ones."""
        a_solver = cast(AllenIntervalNetworkSolver, self.constraint_solvers[0])
        a_solver.revert(i)

    @property
    def num_bookmarks(self) -> int:
        """Number of bookmarks currently saved."""
        a_solver = cast(AllenIntervalNetworkSolver, self.constraint_solvers[0])
        return a_solver.num_bookmarks

    def get_activities_with_symbols(
        self, component_or_values: str | list[str], values: list[str] | None = None
    ) -> list[SymbolicVariableActivity]:
        """Activities whose symbolic value intersects ``values``, either
        network-wide (single-arg form) or restricted to ``component`` (two-
        arg form, matching Java's ``(component, values)``/``(values)``
        overloads)."""
        vars_: list[Variable]
        if values is None:
            vars_ = self.constraint_network.get_variables()
            resolved_values = cast("list[str]", component_or_values)
        else:
            vars_ = self.constraint_network.get_variables(cast(str, component_or_values))
            resolved_values = values
        return self._get_activities_with_symbols_helper(vars_, resolved_values)

    @staticmethod
    def _get_activities_with_symbols_helper(
        vars_: list[Variable], values: list[str]
    ) -> list[SymbolicVariableActivity]:
        ret: list[SymbolicVariableActivity] = []
        for var in vars_:
            act = cast(SymbolicVariableActivity, var)
            symbol_list = act.symbolic_variable.symbols
            for value in values:
                if value in symbol_list:
                    ret.append(act)
                    break
        return ret
