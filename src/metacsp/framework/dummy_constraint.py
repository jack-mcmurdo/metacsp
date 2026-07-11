"""Port of framework/DummyConstraint.java."""

from __future__ import annotations

from metacsp.framework.constraint import Constraint
from metacsp.framework.dummy_variable import DummyVariable

__all__ = ["DummyConstraint"]


class DummyConstraint(Constraint):
    """Binary constraint used to connect a DummyVariable hub to each Variable
    in the scope of a hyperedge (n-ary) Constraint (see ConstraintNetwork)."""

    def __init__(self, edge_label: str) -> None:
        super().__init__()
        self._edge_label = edge_label

    def __str__(self) -> str:
        return f'Dummy constraint "{self._edge_label}"'

    @property
    def edge_label(self) -> str:
        return self._edge_label

    def clone(self) -> DummyConstraint:
        dc = DummyConstraint(self._edge_label)
        dc.scope = self.scope
        dc.auto_removable = self.auto_removable
        return dc

    def is_equivalent(self, c: Constraint) -> bool:
        if not isinstance(c, DummyConstraint):
            return False
        return self._edge_label == c.edge_label

    def get_dummy_variable(self) -> DummyVariable | None:
        for v in self.scope:
            if isinstance(v, DummyVariable):
                return v
        return None
