"""Port of framework/Constraint.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable

__all__ = ["Constraint"]


class Constraint(ABC):
    """Represents n-ary constraints in the MetaCSP framework.

    Unlike Variable, Java's Constraint does not override equals()/hashCode(),
    so it compares by identity -- Python's default object identity equality
    already matches this, so __eq__/__hash__ are intentionally left alone (C3).
    """

    num_ids: ClassVar[int] = 0

    def __init__(self) -> None:
        self._solvers_to_skip: set[ConstraintSolver] | None = None
        self.masked: bool = False
        self.id: int = 0
        self._scope: list[Variable] = []
        self._annotation: Any = None
        self._auto_removable: bool = False
        self._color: Any = "black"
        self.logger = get_logger(type(self))

    def skip_solver(self, *solvers: ConstraintSolver) -> None:
        """Provide a list of solvers that should not process this constraint."""
        if self._solvers_to_skip is None:
            self._solvers_to_skip = set()
        self._solvers_to_skip.update(solvers)

    @property
    def is_masked(self) -> bool:
        """True iff this Constraint is masked (hidden from constraint-network views)."""
        return self.masked

    def mask(self) -> None:
        """Mark this Constraint as masked."""
        self.masked = True

    def unmask(self) -> None:
        """Unmark this Constraint, making it visible again."""
        self.masked = False

    @property
    def is_unary(self) -> bool:
        """True iff this Constraint's scope only refers to one Variable."""
        one_var = self.scope[0]
        return all(v == one_var for v in self.scope[1:])

    def is_skippable_solver(self, cs: ConstraintSolver) -> bool:
        """True iff ``cs`` was registered via :meth:`skip_solver` for this Constraint."""
        return self._solvers_to_skip is not None and cs in self._solvers_to_skip

    @property
    def annotation(self) -> Any:
        """Arbitrary user-attached annotation."""
        return self._annotation

    @annotation.setter
    def annotation(self, value: Any) -> None:
        """Set this Constraint's annotation."""
        self._annotation = value

    @abstractmethod
    def __str__(self) -> str: ...

    @property
    @abstractmethod
    def edge_label(self) -> str:
        """Value drawn by ConstraintNetwork rendering methods."""

    @property
    def scope(self) -> list[Variable]:
        """The Variables this Constraint refers to."""
        return self._scope

    @scope.setter
    def scope(self, value: list[Variable]) -> None:
        """Set this Constraint's scope."""
        self._scope = value

    @abstractmethod
    def clone(self) -> Constraint:
        """Return an independent copy of this Constraint."""
        ...

    @abstractmethod
    def is_equivalent(self, c: Constraint) -> bool:
        """Assess "equivalence" between two constraints (not used for equals/hash)."""

    @property
    def description(self) -> str:
        """Short human-readable description of this Constraint (defaults to the class name)."""
        return type(self).__name__

    @property
    def auto_removable(self) -> bool:
        """True iff this Constraint should be removed automatically once it becomes irrelevant."""
        return self._auto_removable

    @auto_removable.setter
    def auto_removable(self, value: bool) -> None:
        """Set whether this Constraint is auto-removable."""
        self._auto_removable = value

    @property
    def color(self) -> Any:
        """Color used when rendering this Constraint."""
        return self._color

    @color.setter
    def color(self, value: Any) -> None:
        """Set the color used when rendering this Constraint."""
        self._color = value
