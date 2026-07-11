"""Port of framework/ConstraintSolver.java."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, ClassVar, Sequence

from metacsp.exceptions import ConstraintNotFound, IllegalVariableRemoval, VariableNotFound
from metacsp.framework.constraint import Constraint
from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.dummy_constraint import DummyConstraint
from metacsp.framework.variable import Variable
from metacsp.utility.logging import get_logger

__all__ = ["ConstraintSolver"]


class ConstraintSolver(ABC):
    """Common infrastructure for all constraint solvers.

    Maintains a ConstraintNetwork and provides methods to create/remove
    Variables, add/remove Constraints, and drive propagation. Concrete
    solvers implement the ``*_sub`` hook methods and :meth:`propagate`.
    """

    class Options(Enum):
        """General class options.

        AUTO_PROPAGATE: call propagate() automatically (default MANUAL_PROPAGATE).
        NO_PROP_ON_VAR_CREATION: skip auto-propagation on variable creation.
        DOMAINS_AUTO_INSTANTIATED: skip the domains-instantiated check before
        propagation (default DOMAINS_MANUALLY_INSTANTIATED).
        """

        AUTO_PROPAGATE = auto()
        NO_PROP_ON_VAR_CREATION = auto()
        MANUAL_PROPAGATE = auto()
        DOMAINS_AUTO_INSTANTIATED = auto()
        DOMAINS_MANUALLY_INSTANTIATED = auto()

    num_calls: ClassVar[int] = 0
    nesting: ClassVar[int] = 0
    spacing: ClassVar[str] = "  "

    def __init__(self, constraint_types: Sequence[type], variable_type: type) -> None:
        self.the_network = ConstraintNetwork(self)
        self.constraint_types = list(constraint_types)
        self.variable_type = variable_type
        self._ids = 0
        self.name: str | None = None
        self._autoprop = False
        self._no_prop_on_var_creation = False
        self._domains_auto_instantiated = False
        self._skip_propagation = False
        self._domains_instantiated = False
        self._components: dict[str, list[Variable]] = {}
        self.logger = get_logger(type(self))
        self.register_value_choice_functions()

    def set_name(self, name: str) -> None:
        self.name = name

    def set_options(self, *ops: ConstraintSolver.Options) -> None:
        for op in ops:
            if op is ConstraintSolver.Options.AUTO_PROPAGATE:
                self._autoprop = True
            elif op is ConstraintSolver.Options.NO_PROP_ON_VAR_CREATION:
                self._no_prop_on_var_creation = True
            elif op is ConstraintSolver.Options.MANUAL_PROPAGATE:
                self._autoprop = False
            elif op is ConstraintSolver.Options.DOMAINS_AUTO_INSTANTIATED:
                self._domains_auto_instantiated = True
            elif op is ConstraintSolver.Options.DOMAINS_MANUALLY_INSTANTIATED:
                self._domains_auto_instantiated = False

    def get_option(self, op: ConstraintSolver.Options) -> bool:
        if op is ConstraintSolver.Options.AUTO_PROPAGATE:
            return self._autoprop
        if op is ConstraintSolver.Options.NO_PROP_ON_VAR_CREATION:
            return self._no_prop_on_var_creation
        if op is ConstraintSolver.Options.MANUAL_PROPAGATE:
            return not self._autoprop
        if op is ConstraintSolver.Options.DOMAINS_AUTO_INSTANTIATED:
            return self._domains_auto_instantiated
        if op is ConstraintSolver.Options.DOMAINS_MANUALLY_INSTANTIATED:
            return not self._domains_auto_instantiated
        return False

    def is_compatible(self, c: Constraint) -> bool:
        """True iff the given Constraint is compatible with this solver
        (used to ignore incompatible constraints in MultiConstraintSolvers)."""
        return any(isinstance(c, con_type) for con_type in self.constraint_types)

    @abstractmethod
    def propagate(self) -> bool:
        """Propagate the constraint network; return whether it succeeded."""

    # --- adding constraints ---

    def add_constraint(self, c: Constraint) -> bool:
        return self.add_constraints(c)

    def add_constraint_no_propagation(self, c: Constraint) -> bool:
        self._skip_propagation = True
        self.add_constraints(c)
        self._skip_propagation = False
        return True

    def add_constraints_debug(self, *c: Constraint) -> Constraint | None:
        """Add constraints one at a time; return the first one that fails
        (rolling back those added so far), or None if all succeed."""
        added_so_far: list[Constraint] = []
        for con in c:
            if not self.add_constraint(con):
                self.remove_constraints(added_so_far)
                return con
            added_so_far.append(con)
        return None

    def add_constraints_no_propagation(self, *c: Constraint) -> bool:
        self._skip_propagation = True
        self.add_constraints(*c)
        self._skip_propagation = False
        return True

    def add_constraints(self, *c: Constraint) -> bool:
        """Add a batch of constraints in a single propagation; all are
        accepted or rejected together."""
        if not c:
            return True
        incompatible = [
            con for con in c if not (self.is_compatible(con) and not con.is_skippable_solver(self))
        ]
        to_add = [con for con in c if con not in incompatible]
        if not to_add:
            return True

        self.mask_constraints(list(c))
        if self.add_constraints_sub(to_add):
            for con in to_add:
                self.the_network.add_constraint(con)
            if not self._skip_propagation and self._autoprop and self._check_domains_instantiated():
                if self.propagate():
                    self.logger.debug("Added and propagated constraints %s", to_add)
                    self.unmask_constraints(list(c))
                    return True
                self.remove_constraints(to_add)
                self.logger.debug("Failed to add constraints %s", to_add)
            else:
                self.logger.debug(
                    "Added constraints %s BUT DELAYED PROPAGATION (autoprop = %s)",
                    to_add,
                    self._autoprop,
                )
                self.unmask_constraints(list(c))
                return True
        if not self._skip_propagation and self._autoprop and self._check_domains_instantiated():
            self.propagate()
        self.unmask_constraints(list(c))
        return False

    @abstractmethod
    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        """Add multiple constraints; return True on success."""

    # --- removing constraints ---

    def remove_constraint(self, c: Constraint | None) -> None:
        if c is not None:
            self.remove_constraints([c])

    def remove_constraints(self, c: list[Constraint]) -> None:
        if not c:
            return
        incompatible = []
        for con in c:
            if self.is_compatible(con) and not con.is_skippable_solver(self):
                if not self.the_network.contains_constraint(con):
                    self.logger.info("Gonna fail - the constraint type is %s", type(con).__name__)
                    raise ConstraintNotFound(con)
            else:
                incompatible.append(con)
        to_remove = [con for con in c if con not in incompatible]
        self.remove_constraints_sub(to_remove)
        for con in to_remove:
            self.the_network.remove_constraint(con)
        if not self._skip_propagation and self._autoprop and self._check_domains_instantiated():
            self.propagate()
        self.logger.debug("Removed constraints %s", to_remove)

    @abstractmethod
    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        """Remove a batch of constraints."""

    # --- creating variables ---

    def create_variable(self, component: str | None = None) -> Variable:
        return self.create_variables(1, component)[0]  # type: ignore[index]

    def create_variables(self, num: int, component: str | None = None) -> list[Variable] | None:
        ret = self.create_variables_sub_component(num, component)
        if ret is None:
            return None
        for v in ret:
            self.the_network.add_variable(v)
        if (
            not self._skip_propagation
            and self._autoprop
            and self._check_domains_instantiated()
            and not self._no_prop_on_var_creation
        ):
            self.propagate()
        self.logger.debug("Created variables %s", ret)
        return ret

    @abstractmethod
    def create_variables_sub(self, num: int) -> list[Variable] | None:
        """Create a batch of Variables for this solver (primary hook)."""

    def create_variables_sub_component(
        self, num: int, component: str | None
    ) -> list[Variable] | None:
        """Create a batch of Variables and tag them with a component.

        Default implementation delegates to :meth:`create_variables_sub` then
        :meth:`set_component`; MultiConstraintSolver (M3) overrides this hook
        directly to create variables with component-specific "ingredients".
        """
        ret = self.create_variables_sub(num)
        if ret and component is not None:
            self.logger.debug("Set component of %s to %s", ret, component)
            self.set_component(component, *ret)
        return ret

    def _check_domains_instantiated(self) -> bool:
        if self._domains_auto_instantiated:
            return True
        if self.the_network.check_domains_instantiated() is None:
            self._domains_instantiated = True
            return True
        return False

    def set_component(self, component: str, *vars: Variable) -> None:
        """Tag variables under a component (used e.g. by timeline plotting)."""
        for var in vars:
            if var.component is not None and var.component != component:
                self._components[var.component].remove(var)
        if component not in self._components:
            self._components[component] = []
        for var in vars:
            self._components[component].append(var)

    # --- removing variables ---

    def remove_variable(self, v: Variable) -> None:
        self.remove_variables([v])

    def _remove_dummy_constraint(self, c: DummyConstraint) -> Constraint | None:
        dv = c.get_dummy_variable()
        if dv is None:
            return None
        return self.the_network.find_hyperedge_constraint(dv)

    def remove_variables(self, v: list[Variable]) -> None:
        incident_revised: dict[Constraint, None] = {}
        solvers_to_dep_vars: dict[ConstraintSolver, list[Variable]] = {}

        for var in v:
            if not self.the_network.contains_variable(var):
                raise VariableNotFound(var)
            incident = self.the_network.get_incident_edges(var)
            for con in incident:
                if not con.auto_removable and not isinstance(con, DummyConstraint):
                    raise IllegalVariableRemoval(var, self.the_network.get_incident_edges(var))
                elif isinstance(con, DummyConstraint):
                    to_remove = self._remove_dummy_constraint(con)
                    if to_remove is not None:
                        incident_revised[to_remove] = None
                else:
                    incident_revised[con] = None

            for dep_var in var.dependent_variables:
                solvers_to_dep_vars.setdefault(dep_var.constraint_solver, []).append(dep_var)

        for cs, dep_vars in solvers_to_dep_vars.items():
            cs.remove_variables(dep_vars)
            self.logger.debug("Removed %d dependent variables", len(dep_vars))

        self.remove_constraints(list(incident_revised))

        self.remove_variables_sub(v)
        for var in v:
            self.the_network.remove_variable(var)
        for vec in self._components.values():
            for var in v:
                if var in vec:
                    vec.remove(var)
        if not self._skip_propagation and self._autoprop and self._check_domains_instantiated():
            self.propagate()
        self.logger.debug("Removed variables %s", v)

    @abstractmethod
    def remove_variables_sub(self, v: list[Variable]) -> None:
        """Remove a batch of Variables."""

    # --- queries ---

    @property
    def constraint_network(self) -> ConstraintNetwork:
        return self.the_network

    @constraint_network.setter
    def constraint_network(self, new_cn: ConstraintNetwork) -> None:
        self.the_network = new_cn

    def get_variable(self, id: int) -> Variable | None:
        return self.the_network.get_variable(id)

    def get_id(self, var: Variable) -> int:
        for i, v in enumerate(self.get_variables()):
            if v == var:
                return i
        return -1

    def get_variables(
        self, component: str | None = None, *markings_to_exclude: Any
    ) -> list[Variable]:
        if component is None:
            return self.the_network.get_variables()
        ret = self._components.get(component)
        if ret is None:
            return []
        if not markings_to_exclude:
            return list(ret)
        filtered = []
        for v in ret:
            excluded = v.marking is not None and any(m == v.marking for m in markings_to_exclude)
            if not excluded:
                filtered.append(v)
        return filtered

    def get_constraints(
        self, from_: Variable | None = None, to: Variable | None = None
    ) -> list[Constraint]:
        if from_ is None and to is None:
            return self.the_network.get_constraints()
        return [
            con
            for con in self.get_constraints()
            if len(con.scope) == 2 and con.scope[0] == from_ and con.scope[1] == to
        ]

    def get_component(self, v: Variable) -> str | None:
        for name, vars_ in self._components.items():
            if v in vars_:
                return name
        return None

    def __str__(self) -> str:
        return f"{type(self).__name__} ({self.name or ''}): {self.get_variables()}"

    @property
    def description(self) -> str:
        spacer = ConstraintSolver.spacing * ConstraintSolver.nesting
        ret = f"{spacer}[{type(self).__name__} vars: [{self.variable_type.__name__}] constraints: ["
        ret += "".join(c.__name__ for c in self.constraint_types)
        return ret + "]]"

    def deplenish(self) -> None:
        """Remove all constraints and variables from the network."""
        self.remove_constraints_sub(self.get_constraints())
        self.remove_variables(self.get_variables())

    @property
    def components(self) -> dict[str, list[Variable]]:
        return self._components

    @components.setter
    def components(self, value: dict[str, list[Variable]]) -> None:
        self._components = value

    def contains_variable(self, v: Variable) -> bool:
        return self.the_network.contains_variable(v)

    @abstractmethod
    def register_value_choice_functions(self) -> None: ...

    def mask_constraints(self, constraints: list[Constraint]) -> None:
        """Hook called before propagation with the constraints being added;
        no-op by default, override for solver-specific masking."""

    def unmask_constraints(self, constraints: list[Constraint]) -> None:
        """Hook called after propagation with the constraints that were
        added; no-op by default, reverses :meth:`mask_constraints`."""
