"""Change-notification event for ConstraintNetwork (D2, replaces JUNG
ObservableGraph + Swing repaints; the observer-layer hook for a future
browser viewer -- see docs/VIZ.md, written in M21).

Java's ConstraintNetworkChangeListener (a single-method callback interface)
is not ported as its own class per C4: ConstraintNetwork.add_change_listener
accepts any callable ``Callable[[ConstraintNetworkChangeEvent], None]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Union

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["ConstraintNetworkChangeEvent", "ChangeKind"]

ChangeKind = Literal["variable_added", "variable_removed", "constraint_added", "constraint_removed"]


@dataclass(frozen=True)
class ConstraintNetworkChangeEvent:
    """Notifies a ConstraintNetwork change listener of one added/removed item."""

    kind: ChangeKind
    payload: Union["Variable", "Constraint"]
