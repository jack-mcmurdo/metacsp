"""Port of multi/activity/Timeline.java.

The Swing profile viewer (``draw()``, ``utility/UI/PlotBoxTLSmall``) is not
ported -- see D10.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.multi.activity.activity import Activity

__all__ = ["Timeline"]


class Timeline(ABC):
    """A sequence of "pulses" (time points at which some Activity on a given
    component starts or ends) and the values holding between them."""

    def __init__(self, an: Any, component: str, *markings_to_exclude: Any) -> None:
        self._an: ConstraintNetwork = (
            an if isinstance(an, ConstraintNetwork) else an.constraint_network
        )
        self.component = component
        self.markings_to_exclude = markings_to_exclude
        self._pulses: list[int] = []
        self._durations: list[int] = []
        self._compute_pulses()
        self._compute_durations()

    def _compute_origin(self) -> int:
        start_times = [
            v.temporal_variable.est for v in self._an.get_variables() if isinstance(v, Activity)
        ]
        if start_times:
            return min(start_times)
        return 0

    def _compute_pulses(self) -> None:
        st_vars = self._an.get_variables(self.component, *self.markings_to_exclude)
        pulses_temp: list[int] = []
        pulses_temp.append(self._compute_origin() if st_vars else 0)
        for v in st_vars:
            if isinstance(v, Activity):
                start = v.temporal_variable.est
                if start not in pulses_temp:
                    pulses_temp.append(start)
                end = v.temporal_variable.eet
                if end not in pulses_temp:
                    pulses_temp.append(end)
        self._pulses = sorted(pulses_temp)

    def _compute_durations(self) -> None:
        if not self._pulses:
            self._durations = []
        else:
            self._durations = [
                self._pulses[i + 1] - self._pulses[i] for i in range(len(self._pulses) - 1)
            ]

    @property
    @abstractmethod
    def values(self) -> list[Any]:
        """The value(s) holding in each interval between consecutive pulses."""
        ...

    @property
    def pulses(self) -> list[int]:
        """The sorted times at which some Activity on this component starts or ends."""
        return self._pulses

    @property
    def durations(self) -> list[int]:
        """The duration of each interval between consecutive pulses."""
        return self._durations

    def draw(self) -> None:
        """Draw a profile plot of this Timeline.

        The Java Swing ``PlotBoxTLSmall`` viewer is not ported (skip list);
        a browser-based view is future work (D10).
        """
        raise NotImplementedError("the Swing profile viewer is not ported; see D10")

    @property
    def constraint_network(self) -> ConstraintNetwork:
        """The ConstraintNetwork this Timeline was built from."""
        return self._an

    @abstractmethod
    def is_undetermined(self, o: Any) -> bool:
        """True iff no Activity holds a value in the given pulse interval."""
        ...

    @abstractmethod
    def is_critical(self, o: Any) -> bool:
        """True iff the given pulse interval's value is at risk of change."""
        ...

    @abstractmethod
    def is_inconsistent(self, o: Any) -> bool:
        """True iff the given pulse interval's Activity domain was restricted to zero symbols."""
        ...

    def __str__(self) -> str:
        return (
            f"== {self.component} ==\nPulses: {self.pulses}"
            f"\nValues: {self.values}"
            f"\n(Durations: {self.durations})"
        )
