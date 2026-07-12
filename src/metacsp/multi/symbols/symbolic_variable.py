"""Port of multi/symbols/SymbolicVariable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.boolean_sat.boolean_constraint import BooleanConstraint
from metacsp.boolean_sat.boolean_domain import BooleanDomain
from metacsp.boolean_sat.boolean_variable import BooleanVariable
from metacsp.framework.multi.multi_variable import MultiVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable
    from metacsp.multi.symbols.symbolic_variable_constraint_solver import (
        SymbolicVariableConstraintSolver,
    )

__all__ = ["SymbolicVariable"]


class SymbolicVariable(MultiVariable):
    """A variable whose value is a (possibly multi-valued) subset of a
    fixed vocabulary of symbols, represented internally as one BooleanVariable
    per vocabulary symbol."""

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        self.non_solver_domain: list[str] = []
        super().__init__(cs, id, internal_solvers, internal_vars)

    def __lt__(self, other: Variable) -> bool:
        return False

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        solver = cast("SymbolicVariableConstraintSolver", self.constraint_solver)
        if not variables:
            return None
        if not solver.symbols:
            return None

        cons: list[BooleanConstraint] = []

        if solver.single_value:
            # Insert a constraint saying that var must have at exactly one symbol.
            for i in range(len(variables) - 1):
                for j in range(i + 1, len(variables) - 1):
                    c = BooleanConstraint(
                        [cast(BooleanVariable, variables[i]), cast(BooleanVariable, variables[j])],
                        [False, False],
                    )
                    c.auto_removable = True
                    cons.append(c)

        wff = "("
        for i in range(len(variables)):
            if i != len(variables) - 1:
                wff += f"w{i + 1} v ("
            else:
                wff += f"w{i + 1}"
        wff += ")" * len(variables)
        self.logger.debug("Generated internal WFF for variable %d: %s", self.id, wff)
        bvs = [cast(BooleanVariable, v) for v in variables]
        for c in BooleanConstraint.create_boolean_constraints(bvs, wff):
            c.auto_removable = True
            cons.append(c)

        return cons

    @property
    def domain(self) -> Any:
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        pass

    def set_symbolic_domain(self, *symbols: str) -> None:
        solver = cast("SymbolicVariableConstraintSolver", self.constraint_solver)
        solver_symbols = solver.symbols

        solver_symbols_to_make_true = [False] * len(solver_symbols)
        non_solver_domain: list[str] = []
        uses_solver_symbols = False

        for symbol in symbols:
            found = False
            for i, s in enumerate(solver_symbols):
                if s == symbol:
                    found = True
                    solver_symbols_to_make_true[i] = True
                    uses_solver_symbols = True
                    break
            if not found:
                non_solver_domain.append(symbol)

        if uses_solver_symbols:
            from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

            equals_con = SymbolicValueConstraint(SymbolicValueConstraint.Type.VALUESUBSET)
            equals_con.value = solver_symbols_to_make_true
            equals_con.set_from(self)
            equals_con.set_to(self)
            equals_con.auto_removable = True
            self.constraint_solver.add_constraint_no_propagation(equals_con)

        self.non_solver_domain = non_solver_domain

    def __str__(self) -> str:
        return f"{self.id}: {self.symbols}"

    @property
    def symbols(self) -> list[str]:
        ret: list[str] = []
        solver = cast("SymbolicVariableConstraintSolver", self.constraint_solver)
        for i, iv in enumerate(self.internal_variables):
            bv = cast(BooleanVariable, iv)
            bd = cast(BooleanDomain, bv.domain)
            if bd.can_be_true:
                ret.append(solver.get_symbol(i))
        ret.extend(self.non_solver_domain)
        return ret
