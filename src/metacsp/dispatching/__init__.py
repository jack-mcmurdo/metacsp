"""Port of the ``dispatching/`` package: periodic dispatch of PLANNED
activities to per-component :class:`DispatchingFunction` implementations,
driven by a :class:`~metacsp.sensing.constraint_network_animator
.ConstraintNetworkAnimator`'s "Future" activity."""

from metacsp.dispatching.dispatcher import Dispatcher
from metacsp.dispatching.dispatching_function import DispatchingFunction

__all__ = ["Dispatcher", "DispatchingFunction"]
