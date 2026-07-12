"""Port of onLineMonitoring/Rule.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.online_monitoring.monitored_component import MonitoredComponent
    from metacsp.online_monitoring.requirement import Requirement

__all__ = ["Rule"]


class Rule:
    """A hypothesis-generation rule: infers a possibility distribution over
    ``component``'s states from a set of ``requirements`` on other
    :class:`~metacsp.online_monitoring.sensor.Sensor`\\ s."""

    def __init__(
        self,
        component: MonitoredComponent,
        possibilities: list[float],
        *requirements: Requirement,
    ) -> None:
        self.requirements: list[Requirement] = list(requirements)
        self.component = component
        self.possibilities = possibilities
        self.threshold = 0.2
        self.dependency_rank = 0

    def __str__(self) -> str:
        state = self._head_state()
        ret = f"{self.component.name} {state}"
        for r in self.requirements:
            ret += f"\n\t{r}"
        return ret

    def _head_state(self) -> str:
        for i, p in enumerate(self.possibilities):
            if p == 1.0:
                return self.component.states[i]
        return ""

    @property
    def head(self) -> str:
        """The name of ``component``'s state with possibility 1.0 (empty
        string if none). Java ``getHead()``."""
        return self._head_state()
