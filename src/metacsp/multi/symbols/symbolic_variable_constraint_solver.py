"""Port of multi/symbols/SymbolicVariableConstraintSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from metacsp.boolean_sat.boolean_satisfiability_solver import BooleanSatisfiabilitySolver
from metacsp.boolean_sat.boolean_variable import BooleanVariable
from metacsp.framework.constraint_network import mask_constraints as _mask_constraints
from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.multi.symbols.symbolic_variable import SymbolicVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["SymbolicVariableConstraintSolver"]


class SymbolicVariableConstraintSolver(MultiConstraintSolver):
    """A MultiConstraintSolver over SymbolicVariables/SymbolicValueConstraints,
    backed internally by a BooleanSatisfiabilitySolver (each SymbolicVariable
    is a bank of one BooleanVariable per vocabulary symbol)."""

    _this_solver: ClassVar[SymbolicVariableConstraintSolver | None] = None

    def __init__(
        self,
        symbols: list[str] | None = None,
        max_vars: int | None = None,
        propagate_on_var_creation: bool = False,
    ) -> None:
        self.ids = 0
        self.single_value = True
        self.enumerate_sets = True
        self._to_mask: set[Constraint] = set()

        if symbols is None:
            super().__init__(
                [SymbolicValueConstraint],
                SymbolicVariable,
                [BooleanSatisfiabilitySolver(0, 0)],
                [0],
            )
            self.symbols: list[str] = []
            return

        assert max_vars is not None
        max_sat_vars = len(symbols) * max_vars
        max_sat_clauses = (len(symbols) * max_vars) ** 2
        super().__init__(
            [SymbolicValueConstraint],
            SymbolicVariable,
            [BooleanSatisfiabilitySolver(max_sat_vars, max_sat_clauses, propagate_on_var_creation)],
            [len(symbols)],
        )
        self.symbols = list(symbols)
        SymbolicVariableConstraintSolver._this_solver = self
        self.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)
        cast(BooleanSatisfiabilitySolver, self.constraint_solvers[0]).set_enumerate_models(
            self.enumerate_sets
        )

    def _get_unconstrained_variables(self, c: list[Constraint]) -> set[Variable]:
        ret: set[Variable] = set()
        for var in self.the_network.get_variables():
            connected_vars = self.the_network.get_neighboring_variables(var)
            if not connected_vars:
                skip = False
                for con in c:
                    if skip:
                        break
                    for v in con.scope:
                        if v == var:
                            skip = True
                            break
                if not skip:
                    ret.add(var)
        return ret

    @staticmethod
    def union(*variables: Variable) -> Variable:
        """Create a new SymbolicVariable holding the union of the given variables' symbols."""
        solver = SymbolicVariableConstraintSolver._this_solver
        assert solver is not None
        ret = cast(SymbolicVariable, solver.create_variable(variables[0].component))
        unary_equals = SymbolicValueConstraint(SymbolicValueConstraint.Type.VALUEEQUALS)
        unary_value = [False] * len(solver.symbols)
        for var in variables:
            sv = cast(SymbolicVariable, var)
            for symb in sv.symbols:
                for k, sym in enumerate(solver.symbols):
                    if symb == sym:
                        unary_value[k] = True
                        break
        unary_equals.value = unary_value
        unary_equals.set_from(ret)
        unary_equals.set_to(ret)
        solver.add_constraint(unary_equals)
        return ret

    @staticmethod
    def intersection(*variables: Variable) -> Variable | None:
        """Create a new SymbolicVariable holding the intersection of the given variables'
        symbols, or None if the intersection is empty."""
        solver = SymbolicVariableConstraintSolver._this_solver
        assert solver is not None
        unary_equals = SymbolicValueConstraint(SymbolicValueConstraint.Type.VALUEEQUALS)
        all_symbols = solver.symbols
        unary_value = [False] * len(all_symbols)
        at_least_one_value = False
        for i in range(len(all_symbols)):
            found = True
            for var in variables:
                sv = cast(SymbolicVariable, var)
                symbols = sv.symbols
                for k in range(len(symbols)):
                    if symbols[k] == all_symbols[i]:
                        break
                    if k == len(symbols) - 1:
                        found = False
                if not found:
                    break
            if found:
                unary_value[i] = True
                at_least_one_value = True
            else:
                unary_value[i] = False
        if not at_least_one_value:
            return None
        ret = cast(SymbolicVariable, solver.create_variable(variables[0].component))
        unary_equals.value = unary_value
        unary_equals.set_from(ret)
        unary_equals.set_to(ret)
        solver.add_constraint(unary_equals)
        return ret

    def set_enumerate_sets(self, enumerate_sets: bool) -> None:
        """Set whether the underlying SAT solver should enumerate all satisfying models."""
        self.enumerate_sets = enumerate_sets
        cast(BooleanSatisfiabilitySolver, self.constraint_solvers[0]).set_enumerate_models(
            enumerate_sets
        )

    def get_symbol(self, i: int) -> str:
        """The vocabulary symbol at index ``i``."""
        return self.symbols[i]

    def get_boolean_for_symbol(self, symbol: str) -> BooleanVariable | None:
        """The BooleanVariable representing the given vocabulary symbol, if any."""
        for i, s in enumerate(self.symbols):
            if s == symbol:
                return cast(
                    BooleanVariable, self.constraint_solvers[0].constraint_network.get_variable(i)
                )
        return None

    def propagate(self) -> bool:
        """No-op: propagation is delegated entirely to the internal BooleanSatisfiabilitySolver."""
        # Propagation is taken care of by the underlying BooleanSatisfiabilitySolver.
        return True

    def mask_constraints(self, constraints: list[Constraint]) -> None:
        """Mask internal constraints of variables with no neighbors, for SAT solver efficiency."""
        # Mask the internal constraints (BooleanConstraints) that model unary values for
        # variables that have no neighbors -- makes the SAT solver much more efficient.
        unconstrained_variables = self._get_unconstrained_variables(constraints)
        for var in unconstrained_variables:
            sv = cast(SymbolicVariable, var)
            internal_cons = sv.internal_constraints
            if internal_cons:
                _mask_constraints(internal_cons)
        self.logger.debug("Masked internal constraints")

    def unmask_constraints(self, constraints: list[Constraint]) -> None:
        """Unmask all internal constraints previously masked by :meth:`mask_constraints`."""
        self.constraint_solvers[0].constraint_network.unmask_constraints()
        self.logger.debug("Unmasked internal constraints")
