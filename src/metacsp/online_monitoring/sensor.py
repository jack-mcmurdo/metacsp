"""Port of onLineMonitoring/Sensor.java.

A distinct class from :class:`metacsp.sensing.sensor.Sensor` (a different
Java package, ``org.metacsp.onLineMonitoring`` vs ``org.metacsp.sensing``,
with a different purpose): this ``Sensor`` names a monitored source of fuzzy
symbolic readings (a fixed set of named ``states``) that is registered with a
:class:`~metacsp.multi.fuzzy_activity.fuzzy_activity_network_solver
.FuzzyActivityNetworkSolver` and tracks its current possibility distribution
as a sequence of :class:`~metacsp.multi.fuzzy_activity.fuzzy_activity
.FuzzyActivity` readings, ``Meets``-linked to one another as the reading
changes.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, cast

from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)

if TYPE_CHECKING:
    from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity
    from metacsp.multi.fuzzy_activity.fuzzy_activity_network_solver import (
        FuzzyActivityNetworkSolver,
    )

__all__ = ["Sensor"]


class Sensor(ABC):
    """Abstract in Java (``public abstract class Sensor``, declaring no
    abstract methods of its own -- it is abstract purely to force use of a
    concrete subclass); Python does not enforce this since there is no
    ``@abstractmethod`` to anchor it to. Concrete subclasses are
    :class:`~metacsp.online_monitoring.physical_sensor.PhysicalSensor` and
    :class:`~metacsp.online_monitoring.monitored_component.MonitoredComponent`.
    """

    def __init__(self, name: str, *states: str) -> None:
        self.name = name
        self.states: list[str] = list(states)
        self.solver: FuzzyActivityNetworkSolver | None = None
        self.current_possibilities: list[float] = [0.0 for _ in self.states]
        self.current_act: FuzzyActivity | None = None

    def set_current_possibilities(
        self, possibilities: list[float]
    ) -> FuzzyAllenIntervalConstraint | None:
        """Record a new possibility distribution; if it differs from the
        current one, a new :class:`FuzzyActivity` reading is created,
        ``Meets``-linked from the previous reading (if any), and the
        connecting constraint is returned (``None`` if unchanged)."""
        tcon: FuzzyAllenIntervalConstraint | None = None

        diff = False
        for i in range(len(self.current_possibilities)):
            if self.current_possibilities[i] != possibilities[i]:
                diff = True
                break

        # Case: currentPossibilities have changed
        if diff:
            assert self.solver is not None
            act = cast("FuzzyActivity", self.solver.create_variable(self.name))
            act.set_domain(self.states, possibilities)
            self.current_possibilities = possibilities
            if self.current_act is not None:
                tcon = FuzzyAllenIntervalConstraint(FuzzyAllenIntervalConstraint.Type.Meets)
                tcon.from_ = self.current_act
                tcon.to = act
            self.current_act = act

        return tcon
