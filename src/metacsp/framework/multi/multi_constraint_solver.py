"""Port of framework/multi/MultiConstraintSolver.java.

Reflective variable construction (``variableType.getConstructor(...)
.newInstance(...)`` in Java's ``createVariablesSub``) is replaced per C5 by
calling ``self.variable_type(...)`` directly, since Python classes are
first-class objects.
"""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from metacsp.exceptions import ConstraintNotFound, UnimplementedSubVariableException
from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.multi.multi_constraint import MultiConstraint
from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.utility.graph import DelegateTree

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.variable import Variable

__all__ = ["MultiConstraintSolver"]


class MultiConstraintSolver(ConstraintSolver):
    """Extends ConstraintSolver with functionality to deal with
    MultiVariables and MultiConstraints, delegating to a hierarchy of
    internal ConstraintSolvers.

    Subclasses must define how variables are created (the number of internal
    variables per type is given by ``ingredients``, one count per internal
    solver) and how propagation should occur (:meth:`propagate` -- if
    propagation occurs entirely via the underlying solvers this can just
    return True).
    """

    class Options(Enum):
        """Options specific to MultiConstraintSolver. This shadows
        ConstraintSolver.Options (same simple name, different members) --
        Java defines a separate nested ``OPTIONS`` enum here too, hiding the
        parent's when a MultiConstraintSolver's own setOptions()/getOption()
        are used."""

        ALLOW_INCONSISTENCIES = auto()
        FORCE_CONSISTENCY = auto()

    def __init__(
        self,
        constraint_types: list[type],
        variable_type: type,
        internal_solvers: list[ConstraintSolver],
        ingredients: list[int] | None,
    ) -> None:
        super().__init__(constraint_types, variable_type)
        self.constraint_solvers = list(internal_solvers)
        self.ingredients = list(ingredients) if ingredients is not None else None
        self._allow_inconsistencies = False
        self._new_constraint_mapping: dict[Constraint, Constraint] = {}

    @staticmethod
    def get_constraint_solver(
        cs: ConstraintSolver, constraint_solver_class: type
    ) -> ConstraintSolver | None:
        if type(cs) is constraint_solver_class:
            return cs
        if isinstance(cs, MultiConstraintSolver):
            for inner in cs.constraint_solvers:
                ret = MultiConstraintSolver.get_constraint_solver(inner, constraint_solver_class)
                if ret is not None:
                    return ret
        return None

    def set_options(self, *ops: MultiConstraintSolver.Options) -> None:
        for op in ops:
            if op is MultiConstraintSolver.Options.ALLOW_INCONSISTENCIES:
                self._allow_inconsistencies = True
            elif op is MultiConstraintSolver.Options.FORCE_CONSISTENCY:
                self._allow_inconsistencies = False

    def get_option(self, op: MultiConstraintSolver.Options) -> bool:
        if op is MultiConstraintSolver.Options.ALLOW_INCONSISTENCIES:
            return self._allow_inconsistencies
        if op is MultiConstraintSolver.Options.FORCE_CONSISTENCY:
            return not self._allow_inconsistencies
        return False

    def set_ingredients(self, ingredients: list[int] | None) -> None:
        """Set the number of internal variables of each type to create when
        calling :meth:`create_variables_sub`."""
        self.ingredients = list(ingredients)

    # --- constraints ---

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        sorted_cons: dict[ConstraintSolver, list[Constraint]] = {}
        for con in c:
            if isinstance(con, MultiConstraint):
                mv = cast(MultiVariable, con.scope[0])
                for cs in mv.internal_constraint_solvers:
                    if con.propagate_immediately():
                        sorted_cons.setdefault(cs, [])
                        internal_cons = con.internal_constraints
                        if internal_cons is not None:
                            for ic in internal_cons:
                                if not ic.is_skippable_solver(cs):
                                    sorted_cons[cs].append(ic)

        sorted_cons_retract: dict[ConstraintSolver, list[Constraint]] = {}
        for cs, cons in sorted_cons.items():
            if not self._skip_propagation:
                if cs.add_constraints(*cons):
                    self.logger.debug("Added sub-constraints %s", cons)
                    sorted_cons_retract[cs] = cons
                else:
                    for cs1, cons1 in sorted_cons_retract.items():
                        cs1.remove_constraints(cons1)
                    self.logger.debug("Failed to add sub-constraints %s", c)
                    return False
            else:
                cs.add_constraints_no_propagation(*cons)
                self.logger.debug("Added sub-constraints %s (but DELAYED propagation)", cons)

        if not self._instantiate_lifted_constraints(c):
            for cs1, cons1 in sorted_cons_retract.items():
                cs1.remove_constraints(cons1)
            self.logger.debug("Failed to instantiate lifted constraints %s", c)
            return False
        return True

    def _instantiate_lifted_constraints(self, c: list[Constraint]) -> bool:
        new_to_add: list[list[Constraint]] = [[] for _ in self.constraint_types]
        added: list[list[Constraint]] = [[] for _ in self.constraint_types]

        for constr in c:
            for i, ctype in enumerate(self.constraint_types):
                if isinstance(constr, ctype):
                    internal_scope: list[Variable] = []
                    for v in constr.scope:
                        mv = cast(MultiVariable, v)
                        internal_scope.append(mv.internal_variables[i])
                    new_constraint = constr.clone()
                    new_constraint.scope = internal_scope
                    new_to_add[i].append(new_constraint)
                    self._new_constraint_mapping[constr] = new_constraint
                    break

        retract = False
        for i in range(len(self.constraint_types)):
            if retract:
                break
            new_cons = new_to_add[i]
            if new_cons:
                if not self.constraint_solvers[i].add_constraints(*new_cons):
                    retract = True
                else:
                    added[i] = new_cons

        if retract:
            for i, to_retract in enumerate(added):
                if to_retract:
                    self.constraint_solvers[i].remove_constraints(to_retract)
                    to_remove_from_mapping = [
                        old
                        for old, new in self._new_constraint_mapping.items()
                        if new in to_retract
                    ]
                    for old in to_remove_from_mapping:
                        del self._new_constraint_mapping[old]
            return False
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        internal_cons: dict[ConstraintSolver, list[Constraint]] = {}
        for con in c:
            if isinstance(con, MultiConstraint):
                mv = cast(MultiVariable, con.scope[0])
                for cs in mv.internal_constraint_solvers:
                    internal_cons.setdefault(cs, [])
                    if con.internal_constraints:
                        internal_cons[cs].extend(con.internal_constraints)
        for cs, cons in internal_cons.items():
            cs.remove_constraints(cons)

        self._uninstantiate_lifted_constraints(c)

    def _uninstantiate_lifted_constraints(self, c: list[Constraint]) -> None:
        new_to_remove: list[list[Constraint]] = [[] for _ in self.constraint_types]
        for constr in c:
            new_constraint = self._new_constraint_mapping.get(constr)
            if new_constraint is None:
                raise ConstraintNotFound(constr)
            for i, ctype in enumerate(self.constraint_types):
                if type(new_constraint) is ctype:
                    new_to_remove[i].append(new_constraint)
                    break
        for i, to_remove in enumerate(new_to_remove):
            if to_remove:
                self.constraint_solvers[i].remove_constraints(to_remove)
        for constr in c:
            self._new_constraint_mapping.pop(constr, None)

    # --- variables ---

    def remove_variables_sub(self, v: list[Variable]) -> None:
        solvers: dict[ConstraintSolver, list[Variable]] = {}
        for one_var in v:
            if isinstance(one_var, MultiVariable):
                for int_var in one_var.internal_variables:
                    solvers.setdefault(int_var.constraint_solver, []).append(int_var)
        for cs, vars_ in solvers.items():
            self.logger.debug("Removing %d internal variables (%s)", len(vars_), type(cs).__name__)
            cs.remove_variables(vars_)

    def _create_internal_variables(self, ingredients: list[int], num: int) -> list[list[Variable]]:
        ret: list[list[Variable]] = []
        for k, cs in enumerate(self.constraint_solvers):
            one_type = cs.create_variables(ingredients[k] * num)
            self.logger.debug(
                "Created %d internal variables for %s", ingredients[k] * num, type(cs).__name__
            )
            for i in range(num):
                if len(ret) > i:
                    one_var = ret[i]
                else:
                    one_var = []
                    ret.append(one_var)
                for j in range(i * ingredients[k], (i + 1) * ingredients[k]):
                    try:
                        one_var.append(one_type[j])  # type: ignore[index]
                    except TypeError:
                        raise UnimplementedSubVariableException(cs)
        return ret

    def create_variables_sub_ingredients(
        self, ingredients: list[int], num: int, component: str | None
    ) -> list[Variable] | None:
        """Create ``num`` MultiVariables, given the number of internal
        variables to create for each internal solver."""
        internal_vars = self._create_internal_variables(ingredients, num)
        ret: list[Variable] = []
        solvers_to_constraints: dict[ConstraintSolver, list[Constraint]] = {}
        for i in range(num):
            var = self.variable_type(self, self._ids, self.constraint_solvers, internal_vars[i])
            self._ids += 1
            ret.append(var)
            for internal_var in internal_vars[i]:
                if component is not None:
                    internal_var.constraint_solver.set_component(component, internal_var)
                    self.logger.debug("Set component of %s to %s", internal_var, component)
                internal_var.parent_variable = var
            if component is not None:
                var.constraint_solver.set_component(component, var)
                self.logger.debug("Set component of %s to %s", var, component)

            if isinstance(var, MultiVariable):
                internal_cons = var.internal_constraints
                if internal_cons:
                    self.logger.debug("Adding internal constraints for %s", var)
                    for con in internal_cons:
                        cs = con.scope[0].constraint_solver
                        solvers_to_constraints.setdefault(cs, []).append(con)

        for cs, cons in solvers_to_constraints.items():
            if not cs.add_constraints_no_propagation(*cons):
                raise RuntimeError(f"Malformed internal constraints: {cons}")
            self.logger.debug(
                "Added %d internal constraints to %s (but DELAYED propagation)",
                len(cons),
                type(cs).__name__,
            )
        return ret

    def create_variables_sub(self, num: int) -> list[Variable] | None:
        return self.create_variables_sub_ingredients(self.ingredients, num, None)

    def create_variables_sub_component(
        self, num: int, component: str | None
    ) -> list[Variable] | None:
        return self.create_variables_sub_ingredients(self.ingredients, num, component)

    @abstractmethod
    def propagate(self) -> bool: ...

    # --- solver/network hierarchy ---

    def set_constraint_solver(self, i: int, c_solver: ConstraintSolver) -> None:
        self.constraint_solvers[i] = c_solver

    @property
    def description(self) -> str:
        spacer = ConstraintSolver.spacing * ConstraintSolver.nesting
        ret = f"{spacer}[{type(self).__name__} vars: [{self.variable_type.__name__}"
        ret += "] constraints: ["
        ret += ",".join(c.__name__ for c in self.constraint_types)
        ret += "]"
        ConstraintSolver.nesting += 1
        for cs in self.constraint_solvers:
            ret += "\n" + cs.description
        ConstraintSolver.nesting -= 1
        return ret + "]"

    @property
    def constraint_solver_hierarchy(self) -> DelegateTree[ConstraintSolver, str]:
        ret: DelegateTree[ConstraintSolver, str] = DelegateTree()
        ret.set_root(self)
        for i, cs in enumerate(self.constraint_solvers):
            edge_label = f"{i} ({hash(self)})"
            if isinstance(cs, MultiConstraintSolver):
                ret.add_subtree(cs.constraint_solver_hierarchy, self, edge_label)
            else:
                ret.add_child(edge_label, self, cs)
        return ret

    def get_constraint_solvers_from_constraint_solver_hierarchy(
        self, cl: type
    ) -> list[ConstraintSolver]:
        return [cs for cs in self.constraint_solver_hierarchy.vertices() if type(cs) is cl]

    def get_constraint_networks_from_solver_hierarchy(self, cl: type) -> list[ConstraintNetwork]:
        ret = [
            cs.constraint_network
            for cs in self.constraint_solver_hierarchy.vertices()
            if type(cs) is cl
        ]
        if not ret:
            raise RuntimeError(
                f"{type(self).__name__} does not have a {cl.__name__} in its hierarchy"
            )
        return ret

    @property
    def constraint_network_hierarchy(self) -> DelegateTree[ConstraintNetwork, str]:
        ret: DelegateTree[ConstraintNetwork, str] = DelegateTree()
        my_cn = self.constraint_network
        ret.set_root(my_cn)
        for i, cs in enumerate(self.constraint_solvers):
            edge_label = f"{i} ({hash(self)})"
            if isinstance(cs, MultiConstraintSolver):
                ret.add_subtree(cs.constraint_network_hierarchy, my_cn, edge_label)
            else:
                ret.add_child(edge_label, my_cn, cs.constraint_network)
        return ret

    def failure_pruning(self, failure_time: int) -> None:
        self.remove_constraints(self.get_constraints())
        self.remove_variables(self.get_variables())
        for vars_ in self.components.values():
            vars_.clear()

    def register_value_choice_functions(self) -> None:
        pass
