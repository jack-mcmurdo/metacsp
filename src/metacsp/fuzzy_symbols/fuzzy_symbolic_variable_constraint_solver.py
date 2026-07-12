"""Port of fuzzySymbols/FuzzySymbolicVariableConstraintSolver.java.

Solves CSPs where variables are fuzzy sets (FuzzySymbolicVariable) and
constraints are crisp equality/inequality (SymbolicValueConstraint) between
them, via fuzzy arc consistency.

Not ported: Java's ``valueOrdering()``/``sortHashmap()`` (a greedy labeling
step). ``sortHashmap`` builds its sorted map from a fresh, always-empty
``HashMap`` (the line that would populate it via ``psHashMap.clone()`` is
commented out in the source), so it always returns an empty map; the loop in
``valueOrdering()`` that depends on it therefore never executes, leaving
``orderHash`` filled with nulls that nothing else reads (the code that would
read it, a backtracking labeling search, is itself commented out). The net
observable effect of calling it is exactly nothing, so it is omitted here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.fuzzy_symbols.fuzzy_symbolic_domain import FuzzySymbolicDomain
from metacsp.fuzzy_symbols.fuzzy_symbolic_variable import FuzzySymbolicVariable
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity

__all__ = ["FuzzySymbolicVariableConstraintSolver"]


class FuzzySymbolicVariableConstraintSolver(ConstraintSolver):
    """Fuzzy arc consistency over FuzzySymbolicVariables/SymbolicValueConstraints."""

    def __init__(self) -> None:
        self.subs: list[FuzzyActivity] = []
        self.sv_ids = 0
        self._all_con_posib: list[float] = []
        self._possibility_degree = 0.0
        self._false_constraint: list[Constraint] = []
        super().__init__([SymbolicValueConstraint], FuzzySymbolicVariable)
        self.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)
        self.set_options(ConstraintSolver.Options.DOMAINS_MANUALLY_INSTANTIATED)

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return True

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(FuzzySymbolicVariable(self, self.sv_ids))
            self.sv_ids += 1
        return ret

    def get_upper_bound(self) -> float:
        if not self._all_con_posib:
            return 1.0
        return min(self._all_con_posib)

    def get_posibility_degree(self) -> float:
        return self._possibility_degree

    def _check_equality(self, a: dict[str, float], b: dict[str, float]) -> bool:
        return all(a[s] == b[s] for s in a)

    def _check_termination(self, var: dict[int, dict[str, float]]) -> bool:
        is_equal = True
        for i, v in enumerate(self.get_variables()):
            fv = cast(FuzzySymbolicVariable, v)
            if not self._check_equality(fv.get_symbols_and_possibilities(), var[i]):
                var[i] = dict(fv.get_symbols_and_possibilities())
                is_equal = False
        return is_equal

    def _reset_domains(self) -> None:
        for var in self.get_variables():
            cast(FuzzySymbolicVariable, var).reset_domain()

    def _ac_propagation(self, svc_array: list[Constraint]) -> None:
        var: dict[int, dict[str, float]] = {}
        for i, v in enumerate(self.get_variables()):
            var[i] = dict(cast(FuzzySymbolicVariable, v).get_symbols_and_possibilities())

        not_added = False
        self._all_con_posib.clear()
        while True:
            for con in svc_array:
                if not isinstance(con, SymbolicValueConstraint):
                    continue
                if con.type is SymbolicValueConstraint.Type.DIFFERENT:
                    if len(svc_array) == 1:
                        self._all_con_posib.append(0.0)
                    else:
                        self._all_con_posib.append(self._get_sup(con, 0, 1))
                        self._all_con_posib.append(self._get_sup(con, 1, 0))
                if con.type is SymbolicValueConstraint.Type.EQUALS:
                    inf_tmp = self._get_inf(con)
                    self._all_con_posib.append(inf_tmp)
                    if inf_tmp == 0.0:
                        if not self._is_already_marked_as_false(con) and not not_added:
                            self._false_constraint.append(con)
                    not_added = False
            if self._check_termination(var):
                break
        self.subs.clear()

    def _is_already_marked_as_false(self, c: Constraint) -> bool:
        return any(self._is_a_false_clause(fc, c) for fc in self._false_constraint)

    def _is_a_false_clause(self, c1: Constraint, c2: Constraint) -> bool:
        if c1.scope[0].id == c2.scope[0].id and c1.scope[1].id == c2.scope[1].id:
            return True
        if c1.scope[0].id == c2.scope[1].id and c1.scope[0].id == c2.scope[1].id:
            return True
        return False

    def _get_inf(self, c: Constraint) -> float:
        psd: list[float] = []
        intersection: list[str] = []

        var0 = cast(FuzzySymbolicVariable, c.scope[0])
        var1 = cast(FuzzySymbolicVariable, c.scope[1])
        dom0 = cast(FuzzySymbolicDomain, var0.domain)
        dom1 = cast(FuzzySymbolicDomain, var1.domain)

        for st in dom0.get_symbols():
            if st in dom1.get_symbols():
                min_tmp = min(
                    var0.get_symbols_and_possibilities()[st],
                    var1.get_symbols_and_possibilities()[st],
                )
                var0.get_symbols_and_possibilities()[st] = min_tmp
                var1.get_symbols_and_possibilities()[st] = min_tmp
                psd.append(min_tmp)
                intersection.append(st)
        for st in dom0.get_symbols():
            if st not in intersection:
                var0.get_symbols_and_possibilities()[st] = 0.0
        for st in dom1.get_symbols():
            if st not in intersection:
                var1.get_symbols_and_possibilities()[st] = 0.0

        return max(psd)

    def _get_sup(self, c: Constraint, from_: int, to: int) -> float:
        values: list[float] = []
        var_from = cast(FuzzySymbolicVariable, c.scope[from_])
        var_to = cast(FuzzySymbolicVariable, c.scope[to])
        dom_from = cast(FuzzySymbolicDomain, var_from.domain)
        dom_to = cast(FuzzySymbolicDomain, var_to.domain)
        symbols_from = dom_from.get_symbols()
        symbols_to = dom_to.get_symbols()

        max_: list[float] = [0.0] * len(symbols_from)
        for i in range(len(symbols_from)):
            tmp: list[float] = []
            for j in range(len(symbols_to)):
                if symbols_from[i] != symbols_to[j]:
                    tmp.append(var_to.get_symbols_and_possibilities()[symbols_to[j]])
            max_[i] = max(tmp)

        for i, st in enumerate(symbols_from):
            t = min(var_from.get_symbols_and_possibilities()[st], max_[i])
            values.append(t)
            var_from.get_symbols_and_possibilities()[st] = t
        return max(values)

    def _propagate_fuzzy_values(self, svc_array: list[Constraint]) -> None:
        self._ac_propagation(svc_array)

    def propagate(self) -> bool:
        self._reset_domains()
        cons = self.get_constraints()
        self._propagate_fuzzy_values(cons)
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def set_var_of_sub_graph(self, subs: list[FuzzyActivity]) -> None:
        self.subs = subs

    def get_false_constraint(self) -> list[Constraint]:
        return self._false_constraint

    def reset_false_clauses(self) -> None:
        self._false_constraint.clear()

    def register_value_choice_functions(self) -> None:
        pass
