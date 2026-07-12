"""Port of onLineMonitoring/Requirement.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
        FuzzyAllenIntervalConstraint,
    )
    from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
    from metacsp.online_monitoring.sensor import Sensor

__all__ = ["Requirement"]


class Requirement:
    """One requirement of a :class:`~metacsp.online_monitoring.rule.Rule`:
    the possibility distribution a given :class:`~metacsp.online_monitoring
    .sensor.Sensor` must exhibit (``v_cons``), related to the rule's head by
    a fuzzy Allen relation (``t_cons``)."""

    def __init__(
        self,
        sensor: Sensor | None = None,
        possibilities: list[float] | None = None,
        v_cons: SymbolicValueConstraint.Type | None = None,
        t_cons: FuzzyAllenIntervalConstraint.Type | None = None,
    ) -> None:
        self.sensor = sensor
        self.possibilities = possibilities
        self.v_cons = v_cons
        self.t_cons = t_cons

    def __str__(self) -> str:
        state = ""
        assert self.sensor is not None and self.possibilities is not None
        for i, p in enumerate(self.possibilities):
            if p == 1.0:
                state = self.sensor.states[i]
                break
        return f"{self.sensor.name} {{{self.v_cons},{self.t_cons}}} {state}"
