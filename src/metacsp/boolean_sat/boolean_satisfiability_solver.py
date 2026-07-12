"""Port of booleanSAT/BooleanSatisfiabilitySolver.java (D5).

Uses ``pysat.solvers.Minisat22`` in place of SAT4J. Unlike SAT4J,
``Minisat22.add_clause`` never raises for an immediately-contradictory unit
clause (it's simply reflected in the next ``solve()`` call), so the Java
per-clause ``ContradictionException`` handling collapses into a single
post-hoc ``solve()`` check. Model enumeration mirrors the Java loop exactly:
solve, read the model, add its negation as a blocking clause, repeat.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, cast

from pysat.solvers import Minisat22

from metacsp.boolean_sat.boolean_constraint import BooleanConstraint
from metacsp.boolean_sat.boolean_domain import BooleanDomain
from metacsp.boolean_sat.boolean_variable import BooleanVariable
from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.domain import Domain
from metacsp.framework.value_choice_function import ValueChoiceFunction

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["BooleanSatisfiabilitySolver"]

MAX_SAT_VARS = 1000000
MAX_SAT_CLAUSES = 500000


class _ModelValueChoiceFunction(ValueChoiceFunction):
    def __init__(self, models: list[dict[BooleanVariable, bool]], index: int) -> None:
        self.models = models
        self.index = index

    def get_value(self, dom: Domain) -> Any:
        value = self.models[self.index].get(cast(BooleanVariable, dom.variable))
        if value is not None:
            return value
        return True


class _DefaultModelValueChoiceFunction(ValueChoiceFunction):
    def get_value(self, dom: Domain) -> Any:
        return True


class BooleanSatisfiabilitySolver(ConstraintSolver):
    """Reasons about Boolean Satisfiability problems: variables are
    BooleanVariables, constraints are disjunctive BooleanConstraints (the
    conjunction of all BooleanConstraints in a ConstraintNetwork is a CNF
    formula)."""

    MAX_SAT_VARS = MAX_SAT_VARS
    MAX_SAT_CLAUSES = MAX_SAT_CLAUSES

    def __init__(
        self,
        max_vars: int = MAX_SAT_VARS,
        max_clauses: int = MAX_SAT_CLAUSES,
        propagate_on_var_creation: bool = True,
    ) -> None:
        # Set before super().__init__() -- it calls register_value_choice_functions()
        # (as Java's ConstraintSolver constructor also does, before this class's own
        # field initializers would run), which reads _current_models.
        self._current_models: list[dict[BooleanVariable, bool]] = []
        super().__init__([BooleanConstraint], BooleanVariable)
        self.max_vars = max_vars
        self.max_clauses = max_clauses
        self.bv_ids = 1
        self._enumerate_models = True
        self.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)
        if not propagate_on_var_creation:
            self.set_options(ConstraintSolver.Options.NO_PROP_ON_VAR_CREATION)

    def set_enumerate_models(self, enumerate_models: bool) -> None:
        """Set whether :meth:`propagate` enumerates all satisfying models or stops at one."""
        self._enumerate_models = enumerate_models

    def enumerates_models(self) -> bool:
        """True iff this solver enumerates all satisfying models."""
        return self._enumerate_models

    def _reset_current_models(self) -> None:
        self._current_models = []
        self.logger.debug("Reset current models")

    def _update_current_models(self, models: list[list[int]]) -> None:
        self._current_models = []
        for one_model in models:
            a_model: dict[BooleanVariable, bool] = {}
            for lit in one_model:
                bv = cast(BooleanVariable, self.the_network.get_variable(abs(lit)))
                a_model[bv] = lit >= 0
            self._current_models.append(a_model)
        self.register_value_choice_functions()
        self.logger.debug("Updated current models")

    def _update_domains(self, all_models: list[list[int]]) -> None:
        all_vars: set[Variable] = set(self.the_network.get_variables())
        for one_model in all_models:
            for lit in one_model:
                bv = cast(BooleanVariable, self.the_network.get_variable(abs(lit)))
                if bv is not None:
                    if lit < 0:
                        bv.allow_false()
                    else:
                        bv.allow_true()
                    all_vars.discard(bv)
        for var in all_vars:
            bv = cast(BooleanVariable, var)
            bv.allow_false()
            bv.allow_true()

    def propagate(self) -> bool:
        """Solve the CNF formed by unmasked constraints; False iff unsatisfiable."""
        start = time.time()

        sat4j_solver = Minisat22()

        self.logger.debug("Solving SAT problem...")
        cons = self.the_network.unmasked_constraints
        for con in cons:
            bc = cast(BooleanConstraint, con)
            sat4j_solver.add_clause(bc.get_literals())

        all_models: list[list[int]] = []

        if self._enumerate_models:
            if not sat4j_solver.solve():
                return False
            while sat4j_solver.solve():
                one_model = sat4j_solver.get_model()
                if not one_model:
                    break
                all_models.append(one_model)
                neg_clause = [-lit for lit in one_model]
                sat4j_solver.add_clause(neg_clause)
        else:
            if not sat4j_solver.solve():
                return False
            one_model = sat4j_solver.get_model()
            if one_model:
                all_models.append(one_model)

        if all_models:
            self.logger.debug("allmodels[0].length: %d", len(all_models[0]))
            for var in self.the_network.get_variables():
                bv = cast(BooleanVariable, var)
                bv.domain = BooleanDomain(bv, False, False)
            self._update_domains(all_models)
            self._update_current_models(all_models)
        else:
            self._reset_current_models()

        self.logger.debug("Time spent for SAT solving: %f", time.time() - start)
        return True

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        """No-op: constraints are only used when :meth:`propagate` next runs."""
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        """No-op: constraints are only used when :meth:`propagate` next runs."""
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        """Create ``num`` BooleanVariables."""
        ret = []
        for _ in range(num):
            ret.append(BooleanVariable(self, self.bv_ids))
            self.bv_ids += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        """No-op: nothing to release for a BooleanVariable."""
        pass

    def register_value_choice_functions(self) -> None:
        """Register a "modelX" ValueChoiceFunction for BooleanDomain per current SAT model."""
        Domain.remove_value_choice_functions(BooleanDomain)
        if self._current_models:
            for i in range(len(self._current_models)):
                vcf = _ModelValueChoiceFunction(self._current_models, i)
                Domain.register_value_choice_function(BooleanDomain, vcf, f"model{i}")
            self.logger.debug(
                "Updated value choice functions (there are currently %d models)",
                len(self._current_models),
            )
        else:
            vcf = _DefaultModelValueChoiceFunction()
            Domain.register_value_choice_function(BooleanDomain, vcf, "model0")
            self.logger.debug(
                "Updated value choice functions (there is currently only the default model)"
            )
