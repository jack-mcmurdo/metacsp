"""Port of onLineMonitoring/MonitoredComponent.java."""

from __future__ import annotations

from metacsp.online_monitoring.sensor import Sensor

__all__ = ["MonitoredComponent"]


class MonitoredComponent(Sensor):
    """The head component of a :class:`~metacsp.online_monitoring.rule.Rule`:
    a :class:`~metacsp.online_monitoring.sensor.Sensor` whose readings are
    inferred hypotheses rather than raw observations."""

    def __init__(self, name: str, *states: str) -> None:
        super().__init__(name, *states)
