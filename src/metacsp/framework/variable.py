"""Port of framework/Variable.java.

Java serialization support (writeObject/readObject field backup) is not
ported -- see C10, save/load is handled by pickle at the ConstraintNetwork
level instead.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import total_ordering
from typing import TYPE_CHECKING, Any

from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.domain import Domain

__all__ = ["Variable"]


@total_ordering
class Variable(ABC):
    """Represents the decision variables in a Constraint Problem.

    Extended by the abstract class MultiVariable (M3) to accommodate
    variables which are themselves constraint networks.
    """

    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        self._solver = cs
        self.id = id
        self._color: Any = "red"
        self._dependent_variables: list[Variable] = []
        self._marking: Any = None
        self.owner: Any = None
        self.attributes: Any = None
        self._parent_variable: Variable | None = None
        self.logger = get_logger(type(self))

    # --- dependent variables ---

    @property
    def dependent_variables(self) -> list[Variable]:
        """Variables that depend on this Variable; removed when this one is removed."""
        return self._dependent_variables

    @dependent_variables.setter
    def dependent_variables(self, dep_vars: list[Variable]) -> None:
        self._dependent_variables = list(dep_vars)

    def add_dependent_variables(self, *dep_vars: Variable) -> None:
        self._dependent_variables = self._dependent_variables + list(dep_vars)

    def remove_dependent_variables(self, *dep_vars: Variable) -> None:
        self._dependent_variables = [v for v in self._dependent_variables if v not in dep_vars]

    def depends_on(self, var: Variable) -> bool:
        """True iff this Variable depends on the given Variable."""
        return self in var.dependent_variables

    @property
    def is_dependent_variable(self) -> bool:
        """True iff this variable appears in the dependency list of any other
        variable in the same constraint network."""
        for var in self._solver.get_constraint_network().get_variables():
            if self.depends_on(var):
                return True
        return False

    @property
    def recursively_dependent_variables(self) -> list[Variable]:
        """All variables that depend on this Variable or its dependents, plus this Variable."""
        dep_vars: list[Variable] = []
        for dep_var in self.dependent_variables:
            dep_vars.extend(dep_var.recursively_dependent_variables)
        dep_vars.append(self)
        return dep_vars

    # --- variable hierarchy ---

    @property
    def parent_variable(self) -> Variable | None:
        return self._parent_variable

    @parent_variable.setter
    def parent_variable(self, p: Variable | None) -> None:
        self._parent_variable = p

    def get_ancestor_variable(self, cls: type) -> Variable | None:
        """First ancestor MultiVariable of this Variable that is of the given type."""
        aux: Variable | None = self
        while type(aux) is not cls:
            aux = aux.parent_variable if aux is not None else None
            if aux is None:
                return None
        return aux

    @property
    def root_variable(self) -> Variable:
        """The root of this Variable's variable hierarchy."""
        aux: Variable = self
        while aux.parent_variable is not None:
            aux = aux.parent_variable
        return aux

    # --- marking ---

    @property
    def marking(self) -> Any:
        return self._marking

    @marking.setter
    def marking(self, value: Any) -> None:
        self._marking = value
        self.logger.debug("Set marking of variable %s to %s", self.id, value)

    # --- domain (abstract) ---

    @property
    @abstractmethod
    def domain(self) -> Domain | None: ...

    @domain.setter
    @abstractmethod
    def domain(self, d: Domain) -> None: ...

    @property
    def constraint_solver(self) -> ConstraintSolver:
        return self._solver

    @abstractmethod
    def __str__(self) -> str: ...

    @property
    def component(self) -> str | None:
        return self._solver.get_component(self)

    @component.setter
    def component(self, component: str) -> None:
        self._solver.set_component(component, self)

    def __eq__(self, other: object) -> bool:
        """Variables are equal iff they have the same ID and the same class."""
        if isinstance(other, Variable):
            return other.id == self.id and type(other) is type(self)
        return NotImplemented

    def __hash__(self) -> int:
        return self.id

    def __reduce__(self) -> tuple[Any, tuple[Any, Any], dict[str, Any]]:
        """Custom pickling (C10): sets ``self.id`` the instant the object is
        reconstructed, before any of its ``__dict__`` is unpickled.

        Networks routinely have reference cycles through a Variable's own
        ``_solver`` (solver -> constraint_network -> graph -> vertices ->
        this same Variable, used as a dict key). Pickle's default
        reconstruction (``cls.__new__(cls)`` then populate ``__dict__``)
        leaves ``id`` unset while such a cycle is still being resolved, so
        if this Variable is encountered as a dict/set key mid-cycle,
        ``__hash__`` (above) raises ``AttributeError``. Passing ``id`` as a
        constructor argument here means it is set immediately on
        reconstruction, before any nested state (and thus any such cycle)
        is unpickled.
        """
        return (_unpickle_variable, (type(self), self.id), self.__dict__)

    @abstractmethod
    def __lt__(self, other: Variable) -> bool: ...

    @property
    def description(self) -> str:
        return type(self).__name__

    @property
    def color(self) -> Any:
        return self._color

    @color.setter
    def color(self, c: Any) -> None:
        self._color = c


def _unpickle_variable(cls: type[Variable], id: int) -> Variable:
    obj = cls.__new__(cls)
    obj.id = id
    return obj
