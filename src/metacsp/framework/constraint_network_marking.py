"""Port of framework/ConstraintNetworkMarking.java."""

from __future__ import annotations

from enum import Enum, auto

__all__ = ["ConstraintNetworkMarking"]


class ConstraintNetworkMarking:
    """Marks a ConstraintNetwork in the backtracking search process."""

    class Markings(Enum):
        OBSERVABLE = auto()
        IMPOSSIBLE = auto()
        NONE = auto()

    def __init__(self, state: str = "NONE") -> None:
        self._state = state

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, s: str) -> None:
        self._state = s
