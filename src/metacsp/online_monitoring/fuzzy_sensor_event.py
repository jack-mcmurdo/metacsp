"""Port of onLineMonitoring/FuzzySensorEvent.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.online_monitoring.physical_sensor import PhysicalSensor

__all__ = ["FuzzySensorEvent"]


class FuzzySensorEvent:
    """A single timestamped reading: a fuzzy possibility distribution over a
    :class:`~metacsp.online_monitoring.physical_sensor.PhysicalSensor`'s
    states."""

    def __init__(self, sensor: PhysicalSensor, possibilities: list[float], time: int) -> None:
        self.time = time
        self.possibilities = possibilities
        self.sensor = sensor

    def __str__(self) -> str:
        return f"[{self.sensor.name}] {self.sensor.states} = {self.possibilities} @ {self.time}"
