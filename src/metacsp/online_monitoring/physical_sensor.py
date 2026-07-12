"""Port of onLineMonitoring/PhysicalSensor.java."""

from __future__ import annotations

from metacsp.online_monitoring.sensor import Sensor

__all__ = ["PhysicalSensor"]


class PhysicalSensor(Sensor):
    """A concrete :class:`~metacsp.online_monitoring.sensor.Sensor` fed by
    real-world observations (as opposed to
    :class:`~metacsp.online_monitoring.monitored_component.MonitoredComponent`,
    fed by inferred hypotheses)."""

    def __init__(self, name: str, *states: str) -> None:
        super().__init__(name, *states)
