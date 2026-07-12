"""Port of dispatching/DispatchingFunction.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.dispatching.dispatcher import Dispatcher
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity

__all__ = ["DispatchingFunction"]


class DispatchingFunction(ABC):
    """Per-component dispatch behavior, registered with a :class:`~metacsp.
    dispatching.dispatcher.Dispatcher` for one component name.

    Java carries this as an abstract class (not a single-method callback
    interface, C4) since it has two abstract methods plus state (the owning
    ``component`` and, once registered, the owning ``Dispatcher``).
    """

    def __init__(self, component: str) -> None:
        self.component = component
        self._dis: Dispatcher | None = None

    def register_dispatcher(self, dis: Dispatcher) -> None:
        self._dis = dis

    @abstractmethod
    def dispatch(self, act: SymbolicVariableActivity) -> None:
        """Called once when ``act`` transitions PLANNED -> STARTED, i.e. is
        handed off to this component for execution."""

    @abstractmethod
    def skip(self, act: SymbolicVariableActivity) -> bool:
        """Called on every Dispatcher tick, before any other processing of
        ``act``; returning True opts it out of dispatching entirely."""

    def finish(self, *acts: SymbolicVariableActivity) -> None:
        assert self._dis is not None
        self._dis.finish(*acts)

    @property
    def constraint_network(self) -> ConstraintNetwork:
        assert self._dis is not None
        return self._dis.constraint_network

    @property
    def dispatcher(self) -> Dispatcher | None:
        return self._dis
