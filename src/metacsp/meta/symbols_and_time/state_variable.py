"""Port of meta/symbolsAndTime/StateVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.meta.symbols_and_time.schedulable import Schedulable
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.multi.activity.activity import Activity
    from metacsp.time.interval import Interval

__all__ = ["StateVariable"]


class StateVariable(Schedulable):
    """A Schedulable representing a state variable: activities on the same
    state variable conflict when they don't share any allowed state (their
    symbol sets don't intersect)."""

    def __init__(
        self,
        var_oh: VariableOrderingH | None,
        val_oh: ValueOrderingH | None,
        meta_cs: MetaConstraintSolver,
        allowed_states: list[str],
    ) -> None:
        super().__init__(var_oh, val_oh)
        self.peak_collection_strategy = Schedulable.PEAKCOLLECTION.BINARY
        self._states: list[str] = []
        self._reachability: list[list[Interval | None]] = []
        self._set_allowed_states(allowed_states)

    def is_conflicting(self, peak: list[Activity]) -> bool:
        """True iff the peak's two Activities share no allowed symbolic state."""
        if len(peak) != 2:
            return False
        sva0 = cast(SymbolicVariableActivity, peak[0].variable)
        sva1 = cast(SymbolicVariableActivity, peak[1].variable)
        intersection = [
            s for s in sva0.symbolic_variable.symbols if s in sva1.symbolic_variable.symbols
        ]
        # If the intersection is empty these variables do not share symbols
        # and therefore cannot co-exist.
        return not intersection

    def draw(self, network: ConstraintNetwork) -> None:
        """No-op: StateVariable has no dedicated visualization."""
        pass

    def _set_allowed_states(self, st: list[str]) -> None:
        self._states = sorted(st)
        self._reachability = [[None] * len(self._states) for _ in self._states]

    def __str__(self) -> str:
        # Java's toString() is an unfinished "TODO Auto-generated method
        # stub" that returns null; Python's __str__ must return str, so this
        # substitutes the sibling ReusableResource's finished implementation.
        return type(self).__name__

    @property
    def edge_label(self) -> str | None:
        """Always None: StateVariable is not drawn as a graph edge."""
        return None

    def clone(self) -> StateVariable | None:
        """Always None: StateVariable does not support cloning."""
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        """Always False: StateVariable has no notion of equivalence."""
        return False

    @property
    def states(self) -> list[str]:
        """The allowed symbolic states, sorted."""
        return self._states

    @states.setter
    def states(self, value: list[str]) -> None:
        """Set the allowed symbolic states."""
        self._states = value

    def get_ground_solver(self) -> ConstraintSolver | None:
        """Always None: StateVariable has no single ground solver of its own."""
        return None

    def get_meta_values_with_initial_time(
        self, meta_variable: MetaVariable, initial_time: int
    ) -> list[ConstraintNetwork] | None:
        """Overload of :meth:`get_meta_values` accepting (and ignoring) an
        initial time, matching the Java ``getMetaValues(MetaVariable, int)``
        overload."""
        return self.get_meta_values(meta_variable)
