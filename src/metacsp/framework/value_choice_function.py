"""Port of framework/ValueChoiceFunction.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from metacsp.framework.domain import Domain

__all__ = ["ValueChoiceFunction"]


class ValueChoiceFunction(ABC):
    """Basic abstract class for defining value choice functions of a Domain."""

    @abstractmethod
    def get_value(self, dom: Domain) -> Any:
        """Choose a value from the given domain according to this function."""
