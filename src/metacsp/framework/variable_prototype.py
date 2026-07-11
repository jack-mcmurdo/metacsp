"""Port of framework/VariablePrototype.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from metacsp.framework.domain import Domain
from metacsp.framework.variable import Variable

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["VariablePrototype"]


class VariablePrototype(Variable):
    """Represents prototype variables.

    Since the only way to create a Variable is to invoke a ConstraintSolver's
    factory methods (which perform bookkeeping), a variable that is only ever
    used as a prototype can skip all of that via this class. Prototypes are
    not used for reasoning; real Variables are instantiated by concrete
    ConstraintSolvers on the basis of the prototype's parameters.
    """

    next_id: ClassVar[int] = 0

    def __init__(self, cs: ConstraintSolver, *parameters: Any) -> None:
        super().__init__(cs, VariablePrototype.next_id)
        VariablePrototype.next_id += 1
        self.parameters = parameters

    def __lt__(self, other: Variable) -> bool:
        return False

    @property
    def domain(self) -> Domain | None:
        return None

    @domain.setter
    def domain(self, d: Domain) -> None:
        pass

    def __str__(self) -> str:
        return f"{list(self.parameters)} ID {self.id} - {self.marking} |"

    def clone(self) -> VariablePrototype:
        copy = VariablePrototype(self.constraint_solver, *self.parameters)
        return copy
