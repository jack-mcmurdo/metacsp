"""Port of multi/activity/Activity.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable
    from metacsp.multi.allen_interval.allen_interval import AllenInterval

__all__ = ["Activity"]


class Activity(ABC):
    """An activity: something with a temporal placement (AllenInterval) and
    a symbolic description."""

    @property
    @abstractmethod
    def temporal_variable(self) -> AllenInterval:
        """The AllenInterval representing this Activity's temporal value."""

    @property
    @abstractmethod
    def symbols(self) -> list[str]:
        """A description of this Activity's symbolic variable."""

    @property
    @abstractmethod
    def variable(self) -> Variable: ...
