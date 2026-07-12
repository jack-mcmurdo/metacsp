"""Port of multi/symbols/SymbolicValueConstraint.java."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, cast

from metacsp.boolean_sat.boolean_constraint import BooleanConstraint
from metacsp.exceptions import NoSymbolsException, WrongSymbolListException
from metacsp.framework.multi.multi_constraint import MultiConstraint
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver

if TYPE_CHECKING:
    from metacsp.boolean_sat.boolean_variable import BooleanVariable
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.multi.symbols.symbolic_variable import SymbolicVariable
    from metacsp.multi.symbols.symbolic_variable_constraint_solver import (
        SymbolicVariableConstraintSolver,
    )

__all__ = ["SymbolicValueConstraint"]


class SymbolicValueConstraint(MultiConstraint):
    """A constraint over SymbolicVariables: equality/difference/containment
    between two variables' symbol sets, or a unary constraint pinning one
    variable's symbol set to (or away from) a given value."""

    class Type(Enum):
        EQUALS = auto()
        DIFFERENT = auto()
        VALUEEQUALS = auto()
        VALUEDIFFERENT = auto()
        VALUESUBSET = auto()
        CONTAINS = auto()

    def __init__(self, type: Type) -> None:
        super().__init__()
        self.type = type
        self._unary_value: list[bool] | None = None
        self._unary_value_strings: list[str] | None = None

    @property
    def value(self) -> list[str] | None:
        """The unary value (as symbol strings) for VALUE* constraint types."""
        return self._unary_value_strings

    @value.setter
    def value(self, v: list[bool] | list[str]) -> None:
        """Set the unary value, either as a per-vocabulary-symbol bool list or symbol strings."""
        if v and isinstance(v[0], str):
            self._unary_value_strings = list(cast("list[str]", v))
        else:
            self._unary_value = list(cast("list[bool]", v))

    def _create_unary_value_from_strings(self) -> None:
        svcs = cast(
            "SymbolicVariableConstraintSolver | None",
            MultiConstraintSolver.get_constraint_solver(
                self.scope[0].constraint_solver, _svcs_class()
            ),
        )
        if svcs is not None:
            vocabulary = svcs.symbols
            assert self._unary_value_strings is not None
            self._unary_value = [v in self._unary_value_strings for v in vocabulary]

    def _create_strings_from_unary_value(self) -> None:
        svcs = cast(
            "SymbolicVariableConstraintSolver | None",
            MultiConstraintSolver.get_constraint_solver(
                self.scope[0].constraint_solver, _svcs_class()
            ),
        )
        if svcs is not None:
            vocabulary = svcs.symbols
            assert self._unary_value is not None
            self._unary_value_strings = [
                vocabulary[i] for i in range(len(vocabulary)) if self._unary_value[i]
            ]

    def _create_internal_binary_constraints(
        self, f: Variable, t: Variable
    ) -> list[Constraint] | None:
        from metacsp.multi.symbols.symbolic_variable import SymbolicVariable

        if not (isinstance(f, SymbolicVariable) and isinstance(t, SymbolicVariable)):
            return None
        sv_from = cast(SymbolicVariable, f)
        internal_vars_from = sv_from.internal_variables
        svcs = cast("SymbolicVariableConstraintSolver", sv_from.constraint_solver)
        if not svcs.symbols:
            raise NoSymbolsException(sv_from)
        sv_to = cast(SymbolicVariable, t)
        internal_vars_to = sv_to.internal_variables

        Type = SymbolicValueConstraint.Type

        if self.type is Type.EQUALS:
            scope: list[BooleanVariable] = [None] * (len(internal_vars_from) * 2)  # type: ignore[list-item]
            wff = ""
            for i in range(0, len(internal_vars_from) * 2, 2):
                scope[i] = cast("BooleanVariable", internal_vars_from[i // 2])
                scope[i + 1] = cast("BooleanVariable", internal_vars_to[i // 2])
                if i != 0:
                    wff = f"({wff} ^ (w{i + 1} <-> w{i + 2}))"
                else:
                    wff = f"(w{i + 1} <-> w{i + 2})"
            return list(BooleanConstraint.create_boolean_constraints(scope, wff))

        if self.type is Type.CONTAINS:
            scope = [None] * (len(internal_vars_from) * 2)  # type: ignore[list-item]
            wff = ""
            for i in range(0, len(internal_vars_from) * 2, 2):
                scope[i] = cast("BooleanVariable", internal_vars_to[i // 2])
                scope[i + 1] = cast("BooleanVariable", internal_vars_from[i // 2])
                if i == 0:
                    wff = f"(w{i + 1} -> w{i + 2})"
                else:
                    wff = f"({wff} ^ (w{i + 1} -> w{i + 2}))"
            return list(BooleanConstraint.create_boolean_constraints(scope, wff))

        if self.type is Type.DIFFERENT:
            scope = [None] * (len(internal_vars_from) * 2)  # type: ignore[list-item]
            wff = ""
            for i in range(0, len(internal_vars_from) * 2, 2):
                scope[i] = cast("BooleanVariable", internal_vars_from[i // 2])
                scope[i + 1] = cast("BooleanVariable", internal_vars_to[i // 2])
                if i != 0:
                    wff = f"({wff} ^ (~w{i + 1} v ~w{i + 2}))"
                else:
                    wff = f"(~w{i + 1} v ~w{i + 2})"
            return list(BooleanConstraint.create_boolean_constraints(scope, wff))

        if self.type is Type.VALUESUBSET:
            if self._unary_value is None:
                self._create_unary_value_from_strings()
            unary_value = self._unary_value
            assert unary_value is not None
            var_scope: list[BooleanVariable] = []
            wff = ""
            counter = 0
            all_true = True
            for i in range(len(internal_vars_from)):
                try:
                    if not unary_value[i]:
                        all_true = False
                        var_scope.append(cast("BooleanVariable", internal_vars_from[i]))
                        counter += 1
                        wff = f"(~w{counter})" if counter == 1 else f"({wff} ^ (~w{counter}))"
                except IndexError:
                    raise WrongSymbolListException(len(unary_value), len(internal_vars_from))
            if all_true:
                self.logger.debug("Ignored trivial VALUESUBSET constraint (all values true)")
                return []
            return list(BooleanConstraint.create_boolean_constraints(var_scope, wff))

        if self.type is Type.VALUEEQUALS:
            if self._unary_value is None:
                self._create_unary_value_from_strings()
            unary_value = self._unary_value
            assert unary_value is not None
            var_scope = []
            wff = ""
            counter = 0
            all_true = True
            for i in range(len(internal_vars_from)):
                try:
                    if not unary_value[i]:
                        all_true = False
                        var_scope.append(cast("BooleanVariable", internal_vars_from[i]))
                        counter += 1
                        wff = f"(~w{counter})" if counter == 1 else f"({wff} ^ (~w{counter}))"
                    else:
                        var_scope.append(cast("BooleanVariable", internal_vars_from[i]))
                        counter += 1
                        wff = f"(w{counter})" if counter == 1 else f"({wff} ^ (w{counter}))"
                except IndexError:
                    raise WrongSymbolListException(len(unary_value), len(internal_vars_from))
            if all_true:
                self.logger.debug("Ignored trivial VALUEEQUALS constraint (all values true)")
                return []
            return list(BooleanConstraint.create_boolean_constraints(var_scope, wff))

        if self.type is Type.VALUEDIFFERENT:
            if self._unary_value is None:
                self._create_unary_value_from_strings()
            unary_value = self._unary_value
            assert unary_value is not None
            var_scope = []
            wff = ""
            counter = 0
            all_false = True
            for i in range(len(internal_vars_from)):
                try:
                    if unary_value[i]:
                        all_false = False
                        var_scope.append(cast("BooleanVariable", internal_vars_from[i]))
                        counter += 1
                        wff = f"(~w{counter})" if counter == 1 else f"({wff} ^ (~w{counter}))"
                except IndexError:
                    raise WrongSymbolListException(len(unary_value), len(internal_vars_from))
            if all_false:
                self.logger.debug("Ignored trivial VALUEDIFFERENT constraint (all values false)")
                return []
            return list(BooleanConstraint.create_boolean_constraints(var_scope, wff))

        return None

    @property
    def edge_label(self) -> str:
        """Value drawn by ConstraintNetwork rendering methods."""
        Type = SymbolicValueConstraint.Type
        if self.type in (Type.VALUEDIFFERENT, Type.VALUEEQUALS, Type.VALUESUBSET):
            if self._unary_value_strings is None:
                self._create_strings_from_unary_value()
            return f"{self.type.name} {self._unary_value_strings}"
        return self.type.name

    def clone(self) -> SymbolicValueConstraint:
        """Return an independent copy of this constraint."""
        res = SymbolicValueConstraint(self.type)
        if self._unary_value is not None:
            res.value = self._unary_value
        if self._unary_value_strings is not None:
            res.value = self._unary_value_strings
        return res

    def is_equivalent(self, c: Constraint) -> bool:
        """Always False: symbolic value constraints have no notion of equivalence."""
        return False

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        """Compile this constraint's type into internal BooleanConstraints over
        the scoped SymbolicVariables' underlying BooleanVariables."""
        from metacsp.multi.symbols.symbolic_variable import SymbolicVariable

        if not variables:
            return None
        for var in variables:
            if not isinstance(var, SymbolicVariable):
                return None
        cons: list[Constraint] = []
        Type = SymbolicValueConstraint.Type
        if self.type in (Type.EQUALS, Type.DIFFERENT, Type.CONTAINS):
            for i in range(len(variables)):
                for j in range(i + 1, len(variables)):
                    internal_cons = self._create_internal_binary_constraints(
                        variables[i], variables[j]
                    )
                    assert internal_cons is not None
                    cons.extend(internal_cons)
        else:
            for i in range(len(variables)):
                internal_cons = self._create_internal_binary_constraints(variables[i], variables[i])
                assert internal_cons is not None
                cons.extend(internal_cons)
        return cons

    def __str__(self) -> str:
        return f"{self.edge_label} ({self.scope})"

    def set_from(self, f: Variable) -> None:
        """Set the source Variable of this constraint."""
        if not self.scope:
            self.scope = [None, None]  # type: ignore[list-item]
        self.scope[0] = f

    def set_to(self, t: Variable) -> None:
        """Set the destination Variable of this constraint."""
        if not self.scope:
            self.scope = [None, None]  # type: ignore[list-item]
        self.scope[1] = t


def _svcs_class() -> type:
    from metacsp.multi.symbols.symbolic_variable_constraint_solver import (
        SymbolicVariableConstraintSolver,
    )

    return SymbolicVariableConstraintSolver
