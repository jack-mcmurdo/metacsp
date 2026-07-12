"""Port of fuzzyAllenInterval/FuzzyAllenIntervalNetworkSolver.java.

Implements a fuzzified version of Allen's path consistency algorithm.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.domain import Domain
from metacsp.framework.value_choice_function import ValueChoiceFunction
from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.time.qualitative.simple_allen_interval import SimpleAllenInterval
from metacsp.time.qualitative.simple_interval import SimpleInterval

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable
    from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity

__all__ = ["FuzzyAllenIntervalNetworkSolver"]

Type = FuzzyAllenIntervalConstraint.Type
_FRelations = list[list[dict[Type, float]]]


class _IdentityValueChoiceFunction(ValueChoiceFunction):
    def get_value(self, dom: Domain) -> Any:
        return cast(SimpleInterval, dom).interval_name


class FuzzyAllenIntervalNetworkSolver(ConstraintSolver):
    def __init__(self) -> None:
        self.ids = 0
        self._global_possibility_degree = 0.0
        self.subs: list[FuzzyActivity] = []
        self._num_vars = 0
        self._sub_variables: list[Variable] = []
        self._is_sub_graph = False
        self._var_index: dict[int, int] = {}
        self._crisp_cons: list[Constraint] | None = None
        super().__init__([FuzzyAllenIntervalConstraint], SimpleAllenInterval)
        self.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return True

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(SimpleAllenInterval(self, self.ids))
            self.ids += 1
        return ret

    def get_posibility_degree(self) -> float:
        return self._global_possibility_degree

    def propagate(self) -> bool:
        self._is_sub_graph = False
        frelations = self._create_fuzzy_complete_network(self.get_constraints())
        frelations = self._simplify(frelations)
        frelations = self._fuzzy_path_consistency(frelations)
        self._update_global_possibility_degree(frelations)
        return True

    def _is_in_the_sub_graph(self, var_tmp: Variable) -> bool:
        return any(s.internal_variables[0].id == var_tmp.id for s in self.subs)

    def _extract_sub_graph_cons(self, c: list[Constraint]) -> list[Constraint]:
        if not self._is_sub_graph:
            return c
        return [
            con
            for con in c
            if self._is_in_the_sub_graph(con.scope[0]) and self._is_in_the_sub_graph(con.scope[1])
        ]

    def _create_fuzzy_complete_network(self, cns: list[Constraint]) -> _FRelations:
        if self.subs:
            self._is_sub_graph = True
        c = self._extract_sub_graph_cons(cns)

        self._set_num_vars(c)

        num_vars = self._get_num_vars()
        tmp: list[list[FuzzyAllenIntervalConstraint | None]] = [
            [None] * num_vars for _ in range(num_vars)
        ]
        multiple: dict[tuple[int, int], list[FuzzyAllenIntervalConstraint]] = {}

        for con in c:
            if not self._is_sub_graph:
                row = self.get_id(con.scope[0])
                col = self.get_id(con.scope[1])
            else:
                row = self._var_index[con.scope[0].id]
                col = self._var_index[con.scope[1].id]
            fac = cast(FuzzyAllenIntervalConstraint, con)
            if tmp[row][col] is None:
                tmp[row][col] = fac
            else:
                coord = (row, col)
                vec = multiple.get(coord)
                if vec is None:
                    vec = [cast(FuzzyAllenIntervalConstraint, tmp[row][col])]
                    multiple[coord] = vec
                vec.append(fac)

        frelations: _FRelations = []
        for i in range(num_vars):
            con: list[dict[Type, float]] = []
            is_a_crisp_cons = False
            for j in range(num_vars):
                if self._crisp_cons is not None and tmp[i][j] is not None:
                    if self._is_a_crisp_constraint(cast(FuzzyAllenIntervalConstraint, tmp[i][j])):
                        is_a_crisp_cons = True
                if tmp[i][j] is not None:
                    coord = (i, j)
                    if coord not in multiple:
                        if not is_a_crisp_cons:
                            con.append(
                                cast(FuzzyAllenIntervalConstraint, tmp[i][j]).get_possibilities()
                            )
                        else:
                            con.append(
                                cast(FuzzyAllenIntervalConstraint, tmp[i][j]).make_crisp_rel()
                            )
                    else:
                        group = multiple[coord]
                        if not is_a_crisp_cons:
                            poss = group[0].get_possibilities()
                            for h in range(1, len(group)):
                                self._update_relation(poss, group[h].get_possibilities())
                            con.append(poss)
                        else:
                            poss = group[0].make_crisp_rel()
                            for h in range(1, len(group)):
                                self._update_relation(poss, group[h].make_crisp_rel())
                            con.append(poss)
                elif tmp[j][i] is not None:
                    coord = (j, i)
                    if not is_a_crisp_cons:
                        if coord not in multiple:
                            con.append(
                                cast(
                                    FuzzyAllenIntervalConstraint, tmp[j][i]
                                ).get_inverse_possibilities()
                            )
                        else:
                            group = multiple[coord]
                            poss = group[0].get_inverse_possibilities()
                            for h in range(1, len(group)):
                                self._update_relation(poss, group[h].get_inverse_possibilities())
                            con.append(poss)
                    else:
                        if coord not in multiple:
                            con.append(
                                cast(FuzzyAllenIntervalConstraint, tmp[j][i]).get_crisp_inverse()
                            )
                        else:
                            group = multiple[coord]
                            poss = group[0].get_crisp_inverse()
                            for h in range(1, len(group)):
                                self._update_relation(poss, group[h].get_crisp_inverse())
                            con.append(poss)
                else:
                    con.append(self._create_all_fuzzy_allen_relation())
            frelations.append(con)

        return frelations

    def _is_a_crisp_constraint(self, fc: FuzzyAllenIntervalConstraint) -> bool:
        assert self._crisp_cons is not None
        return any(
            fc.from_.id == cc.scope[0].id and fc.to.id == cc.scope[1].id for cc in self._crisp_cons
        )

    def _create_all_fuzzy_allen_relation(self) -> dict[Type, float]:
        row = FuzzyAllenIntervalConstraint.FREKSA_NEIGHBOR[Type.Before.value]
        return {FuzzyAllenIntervalConstraint.lookup_type_by_int(t): 1.0 for t in range(len(row))}

    def _simplify(self, frelations: _FRelations) -> _FRelations:
        num_vars = self._get_num_vars()
        for i in range(num_vars):
            for j in range(num_vars):
                if i != j:
                    from_ = self._get_sub_variable()[i]
                    to = self._get_sub_variable()[j]
                    direct = cast(
                        "FuzzyAllenIntervalConstraint | None",
                        self.constraint_network.get_constraint(from_, to),
                    )
                    inverse = cast(
                        "FuzzyAllenIntervalConstraint | None",
                        self.constraint_network.get_constraint(to, from_),
                    )
                    if direct is not None and inverse is not None:
                        inverse_possibilities = inverse.get_inverse_possibilities()
                        self._update_relation(frelations[i][j], inverse_possibilities)
        return frelations

    def _fuzzy_path_consistency(self, frelations: _FRelations) -> _FRelations:
        num_vars = self._get_num_vars()
        counter = num_vars * num_vars - num_vars
        mark = [[i != j for j in range(num_vars)] for i in range(num_vars)]

        while counter != 0:
            for i in range(num_vars):
                for j in range(num_vars):
                    if i == j:
                        continue
                    if mark[i][j]:
                        mark[i][j] = False
                        counter -= 1
                        for k in range(num_vars):
                            if k == i or k == j:
                                continue
                            hashmap_tmp = dict(frelations[k][j])
                            self._update_relation(
                                frelations[k][j],
                                self._generate_composition(frelations[k][i], frelations[i][j]),
                            )
                            if not self._compare_relation(frelations[k][j], hashmap_tmp):
                                if not mark[k][j]:
                                    mark[k][j] = True
                                    counter += 1

                            hashmap_tmp = dict(frelations[i][k])
                            self._update_relation(
                                frelations[i][k],
                                self._generate_composition(frelations[i][j], frelations[j][k]),
                            )
                            if not self._compare_relation(frelations[i][k], hashmap_tmp):
                                if not mark[i][k]:
                                    mark[i][k] = True
                                    counter += 1
        return frelations

    def _update_global_possibility_degree(self, frelations: _FRelations) -> None:
        max_values = [max(cell.values()) for row in frelations for cell in row]
        self._global_possibility_degree = min(max_values)

    def _compare_relation(self, hm1: dict[Type, float], hm2: dict[Type, float]) -> bool:
        return all(hm1[t] == hm2[t] for t in hm1)

    def _update_relation(self, hm1: dict[Type, float], hm2: dict[Type, float]) -> None:
        for t in hm1:
            hm1[t] = min(hm1[t], hm2[t])

    def _generate_composition(
        self, hm1: dict[Type, float], hm2: dict[Type, float]
    ) -> dict[Type, float]:
        cmp_relation: dict[Type, float] = {}
        for t, v1 in hm1.items():
            for t2, v2 in hm2.items():
                tmp_type = FuzzyAllenIntervalConstraint.TRANSITION_TABLE[t.value][t2.value]
                for t3 in tmp_type:
                    if t3 in cmp_relation:
                        cmp_relation[t3] = max(cmp_relation[t3], min(v1, v2))
                    else:
                        cmp_relation[t3] = min(v1, v2)
        return cmp_relation

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def set_var_of_sub_graph(self, fas: list[FuzzyActivity]) -> None:
        self.subs = fas

    def _get_num_vars(self) -> int:
        return self._num_vars

    def _set_num_vars(self, c: list[Constraint]) -> None:
        self._var_index.clear()
        self._sub_variables = []
        self._num_vars = len(self.get_variables())
        for v in self.get_variables():
            self._sub_variables.append(v)
        if self._is_sub_graph:
            vars_: list[Variable] = []
            for con in c:
                if con.scope[0] not in vars_:
                    vars_.append(con.scope[0])
                    self._var_index[con.scope[0].id] = len(vars_) - 1
                if con.scope[1] not in vars_:
                    vars_.append(con.scope[1])
                    self._var_index[con.scope[1].id] = len(vars_) - 1
            self._num_vars = len(vars_)
            self._sub_variables = vars_

    def _get_sub_variable(self) -> list[Variable]:
        return self._sub_variables

    def set_crisp_cons(self, crisp_cons: list[Constraint]) -> None:
        """Marks the given FuzzyAllenIntervalConstraints as crisp (their
        desired possibility degree should not change; all other relation
        types get possibility 0)."""
        self._crisp_cons = crisp_cons

    def register_value_choice_functions(self) -> None:
        vcf = _IdentityValueChoiceFunction()
        Domain.register_value_choice_function(SimpleInterval, vcf, "ID")
