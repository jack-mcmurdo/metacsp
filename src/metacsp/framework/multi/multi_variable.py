"""Port of framework/multi/MultiVariable.java.

Java serialization support (the ``backupForSerialization``/``FieldOfObject``
machinery used to preserve transient fields across writeObject/readObject) is
not ported -- see C10, save/load is handled by pickle at the ConstraintNetwork
level instead.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from metacsp.framework.multi.multi_domain import MultiDomain
from metacsp.framework.variable import Variable
from metacsp.utility.graph import DelegateTree

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver

__all__ = ["MultiVariable"]


class MultiVariable(Variable):
    """A variable "implemented" by several underlying lower-level Variables.

    Used by MultiConstraintSolvers along with MultiConstraints to maintain
    and propagate multiple CSPs defined by aggregations of variables and
    constraints. Defining a MultiVariable is reduced to creating the internal
    lower-level Variables (done by the caller, passed in as internal_vars)
    and implementing :meth:`create_internal_constraints`.
    """

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id)
        self.internal_solvers = internal_solvers
        self.variables = internal_vars
        self.logger.debug("Set internal variables %s", self.variables)
        self.constraints = self.create_internal_constraints(self.variables)
        self.logger.debug("Created internal constraints %s", self.constraints)

    @abstractmethod
    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        """Define the internal lower-level Constraints of this MultiVariable,
        among the given internal variables."""

    @property
    def internal_variables(self) -> list[Variable]:
        """The lower-level Variables implementing this MultiVariable."""
        return self.variables

    @property
    def internal_constraints(self) -> list[Constraint] | None:
        """The lower-level Constraints among this MultiVariable's internal variables."""
        return self.constraints

    @property
    def internal_constraint_solvers(self) -> list[ConstraintSolver]:
        """The ConstraintSolvers owning this MultiVariable's internal variables."""
        return self.internal_solvers

    @property
    def domain(self) -> MultiDomain:
        """A MultiDomain wrapping the domains of this MultiVariable's internal variables."""
        doms = [v.domain for v in self.variables]
        return MultiDomain(self, *doms)

    @domain.setter
    @abstractmethod
    def domain(self, d: Any) -> None:
        """Left abstract, as in Java: concrete MultiVariable subclasses must
        define how (if at all) an externally supplied domain is applied."""

    @property
    def variable_hierarchy(self) -> DelegateTree[Variable, str]:
        """The hierarchy of Variables underlying this MultiVariable."""
        ret: DelegateTree[Variable, str] = DelegateTree()
        ret.set_root(self)
        my_vars = self.internal_variables
        for i, var in enumerate(my_vars):
            edge_label = f"{i} ({hash(self.constraint_solver)})"
            if isinstance(var, MultiVariable):
                sub_tree = var.variable_hierarchy
                ret.add_subtree(sub_tree, self, edge_label)
            else:
                ret.add_child(edge_label, self, var)
        return ret

    def get_variables_from_variable_hierarchy(self, cls: type) -> list[Variable]:
        """The Variables of a given type in this MultiVariable's variable
        hierarchy."""
        ret = [v for v in self.variable_hierarchy.vertices() if type(v) is cls]
        if not ret:
            raise RuntimeError(
                f"{type(self).__name__} does not have a {cls.__name__} in its hierarchy"
            )
        return ret

    @property
    def description(self) -> str:
        """Human-readable description listing this MultiVariable's internal
        variables and constraints."""
        ret = f"{type(self).__name__}: [vars: ["
        vars_: list[Variable] = []
        for v in self.internal_variables:
            if self.internal_constraints is not None:
                for con in self.internal_constraints:
                    for scope_var in con.scope:
                        if scope_var not in vars_:
                            vars_.append(scope_var)
                    if v not in vars_:
                        vars_.append(v)
            else:
                vars_.append(v)
        ret += ",".join(v.description for v in vars_)
        ret += "] constraints: ["
        if self.internal_constraints is not None:
            ret += ",".join(con.description for con in self.internal_constraints)
        return ret + "]]"

    @property
    def component(self) -> str | None:
        """Name of the component this MultiVariable belongs to, if any."""
        return Variable.component.fget(self)  # type: ignore[union-attr]

    @component.setter
    def component(self, component: str) -> None:
        """Assign this MultiVariable, and all its immediate internal variables, to a component."""
        Variable.component.fset(self, component)  # type: ignore[union-attr]
        tree = self.variable_hierarchy
        for var in tree.children(tree.root):
            var.component = component
