"""Port of sensing/Controllable.java."""

from __future__ import annotations

__all__ = ["Controllable"]


class Controllable:
    """Tags a component as controllable and records the symbols it can be
    commanded to take on.

    Java's commented-out sensor-trace-file parsing methods (a
    ``Controllable``-flavored copy of :class:`~metacsp.sensing.sensor
    .Sensor`'s trace parsing, dead code upstream) are not ported.
    """

    def __init__(self) -> None:
        self._symbols: list[str] = []

    def register_symbols_from_controllable_sensor(self, act: str) -> None:
        self._symbols.append(act)

    @property
    def controllable_symbols(self) -> list[str]:
        """The registered symbols.

        Java ``getContrallbaleSymbols()`` -- a typo for "Controllable" --
        corrected here per C2 (structure preserved, spelling fixed).
        """
        return list(self._symbols)
