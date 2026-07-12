"""Port of framework/meta/FocusConstraint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.constraint import Constraint

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["FocusConstraint"]


class FocusConstraint(Constraint):
    """Marks the set of Variables a MetaConstraintSolver is currently
    focusing search on."""

    def __str__(self) -> str:
        return str(self.scope)

    @property
    def edge_label(self) -> str:
        """Value drawn by ConstraintNetwork rendering methods."""
        return str(self.scope)

    def clone(self) -> FocusConstraint:
        """Return an independent copy of this FocusConstraint."""
        ret = FocusConstraint()
        ret.scope = self.scope
        return ret

    def is_equivalent(self, c: Constraint) -> bool:
        """True iff ``c`` is a FocusConstraint over the same set of Variables."""
        if not isinstance(c, FocusConstraint):
            return False
        for var in self.scope:
            found = False
            for var1 in c.scope:
                if var1 == var:
                    found = True
                    break
            if not found:
                return False
        return True
