"""Port of meta/symbolsAndTime/SymbolicTimeline.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.multi.activity.activity import Activity
from metacsp.multi.activity.timeline import Timeline

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver

__all__ = ["SymbolicTimeline"]


class SymbolicTimeline(Timeline):
    """A Timeline whose values are the union of symbols held by the
    Activities active between each pair of pulses."""

    class ArrayOfStrings:
        """A resizable bag of strings (mirrors the Java inner class, which
        exists to give ``union`` mutation semantics like Java's array
        reassignment)."""

        def __init__(self, strings: list[str]) -> None:
            self.strings = list(strings)

        def __str__(self) -> str:
            return str(self.strings)

        def union(self, other: list[str]) -> None:
            self.strings = self.strings + list(other)

    def __init__(
        self,
        an: ConstraintNetwork | ActivityNetworkSolver,
        component: str,
        *markings_to_exclude: Any,
    ) -> None:
        super().__init__(an, component, *markings_to_exclude)
        self._values: list[SymbolicTimeline.ArrayOfStrings | None] = []
        self._cache_values()

    def _cache_values(self) -> None:
        ret: list[SymbolicTimeline.ArrayOfStrings | None] = [None] * len(self.pulses)
        for i in range(len(self.pulses) - 1):
            if self.markings_to_exclude:
                vars_ = self.constraint_network.get_variables(
                    self.component, *self.markings_to_exclude
                )
            else:
                vars_ = self.constraint_network.get_variables(self.component)
            for var in vars_:
                if isinstance(var, Activity):
                    act = cast(Activity, var)
                    if (
                        act.temporal_variable.est <= self.pulses[i]
                        and act.temporal_variable.eet >= self.pulses[i + 1]
                    ):
                        dom = act.symbols
                        if ret[i] is None:
                            ret[i] = SymbolicTimeline.ArrayOfStrings(dom)
                        else:
                            cast(SymbolicTimeline.ArrayOfStrings, ret[i]).union(dom)
        self._values = ret

    @property
    def values(self) -> list[SymbolicTimeline.ArrayOfStrings | None]:
        return self._values

    def is_undetermined(self, o: Any) -> bool:
        return o is None

    def is_critical(self, o: Any) -> bool:
        if isinstance(o, SymbolicTimeline.ArrayOfStrings):
            return len(o.strings) == 1
        return False

    def is_inconsistent(self, o: Any) -> bool:
        if isinstance(o, SymbolicTimeline.ArrayOfStrings):
            return len(o.strings) == 0
        return False
