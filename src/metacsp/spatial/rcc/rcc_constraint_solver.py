"""Port of spatial/RCC/RCCConstraintSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.spatial.rcc.rcc_constraint import RCCConstraint
from metacsp.spatial.rcc.region import Region

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["RCCConstraintSolver"]


class RCCConstraintSolver(ConstraintSolver):
    """Implements a path consistency algorithm to check the consistency of
    constraint networks with RCC-8 (Region Connection Calculus) constraints."""

    def __init__(self) -> None:
        super().__init__([RCCConstraint], Region)
        self.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)
        self._get_variable_by_id: dict[int, Variable] = {}

    def propagate(self) -> bool:
        if not self.get_constraints():
            return True
        for v in self.get_variables():
            self._get_variable_by_id[v.id] = v
        rcc_rels = self._create_rcc_complete_network(self.get_constraints())
        return self._rcc_path_consistency(rcc_rels)

    def _rcc_path_consistency(self, rcc_rels: list[list[RCCConstraint]]) -> bool:
        num_vars = len(self.get_variables())
        # Need to cycle at least (numVars^2 - numVars) times.
        counter = num_vars * num_vars - num_vars
        mark = [[i != j for j in range(num_vars)] for i in range(num_vars)]

        while counter != 0:  # while the set is not empty
            for i in range(num_vars):
                for j in range(num_vars):
                    if i == j:
                        continue
                    if mark[i][j]:
                        mark[i][j] = False
                        counter -= 1  # remove from set
                        for k in range(num_vars):
                            if k == i or k == j:
                                continue
                            # process relation (k, j)
                            # back up relation (k, j)
                            rcc_tmp = rcc_rels[k][j].clone()
                            # (k, j) <-- (k, j) n (k, i) + (i, j)
                            if not self._update_relation(
                                rcc_rels[k][j],
                                self._generate_composition(rcc_rels[k][i], rcc_rels[i][j]),
                            ):
                                return False
                            # if changed, must re-process (k, j)
                            if not self._compare_relation(rcc_tmp, rcc_rels[k][j]):
                                if not mark[k][j]:
                                    mark[k][j] = True
                                    counter += 1
                            # process relation (i, k)
                            # back up relation (i, k)
                            rcc_tmp = rcc_rels[i][k].clone()
                            # (i, k) <-- (i, k) n (i, j) + (j, k)
                            if not self._update_relation(
                                rcc_rels[i][k],
                                self._generate_composition(rcc_rels[i][j], rcc_rels[j][k]),
                            ):
                                return False
                            # if changed, must re-process (i, k)
                            if not self._compare_relation(rcc_tmp, rcc_rels[i][k]):
                                if not mark[i][k]:
                                    mark[i][k] = True
                                    counter += 1
        return True

    def _compare_relation(self, first: RCCConstraint, second: RCCConstraint) -> bool:
        """True iff every type in ``first`` also appears in ``second``."""
        for t in first.types:
            if t not in second.types:
                return False
        return True

    def _update_relation(
        self, original_relations: RCCConstraint, generated_composition: list[RCCConstraint.Type]
    ) -> bool:
        filtered = [t for t in original_relations.types if t in generated_composition]
        original_relations.types = filtered
        return len(filtered) > 0

    def _generate_composition(
        self, o1: RCCConstraint, o2: RCCConstraint
    ) -> list[RCCConstraint.Type]:
        cmp_relation: list[RCCConstraint.Type] = []
        for t in o1.types:
            for t2 in o2.types:
                tmp_type = RCCConstraint.TRANSITION_TABLE[t.value][t2.value]
                for t3 in tmp_type:
                    if t3 not in cmp_relation:
                        cmp_relation.append(t3)
        return cmp_relation

    def _print_spatial_relation(self, rcc_rels: list[list[RCCConstraint]]) -> str:
        ret = ""
        for i in range(len(rcc_rels)):
            for j in range(len(rcc_rels)):
                if i == j:
                    continue
                ret += f"{i} --> {j} :"
                ret += f"{rcc_rels[i][j]}\n"
        return ret

    def _create_rcc_complete_network(self, c: list[Constraint]) -> list[list[RCCConstraint]]:
        rcc_rels: list[list[RCCConstraint]] = []

        multiple: dict[tuple[int, int], list[RCCConstraint]] = {}
        num_vars = len(self.get_variables())
        tmp: list[list[RCCConstraint | None]] = [[None] * num_vars for _ in range(num_vars)]

        for con in c:
            rcc_con = cast(RCCConstraint, con)
            row = self.get_id(rcc_con.scope[0])
            col = self.get_id(rcc_con.scope[1])
            if tmp[row][col] is None:
                tmp[row][col] = rcc_con
            else:
                coord = (row, col)
                vec = multiple.get(coord)
                if vec is None:
                    vec = [cast(RCCConstraint, tmp[row][col])]
                    multiple[coord] = vec
                vec.append(rcc_con)

        for i in range(num_vars):
            con: list[RCCConstraint] = []
            for j in range(num_vars):
                if tmp[i][j] is not None:
                    coord = (i, j)
                    entry = cast(RCCConstraint, tmp[i][j])
                    if coord not in multiple:
                        con.append(entry)
                    else:
                        # if (a u b u c) u d = (a u b u c u d)
                        t: list[RCCConstraint.Type] = []
                        for m in multiple[coord]:
                            t.extend(m.types)
                        entry.types = t
                        con.append(entry)
                elif tmp[j][i] is not None:
                    coord = (j, i)
                    other = cast(RCCConstraint, tmp[j][i])
                    if coord not in multiple:
                        t = [RCCConstraint.get_inverse_relation(ty) for ty in other.types]
                        inverse = RCCConstraint(*t)
                        inverse.from_ = other.to
                        inverse.to = other.from_
                        con.append(inverse)
                    else:
                        t = []
                        for m in multiple[coord]:
                            t.extend(RCCConstraint.get_inverse_relation(ty) for ty in m.types)
                        inverse = RCCConstraint(*t)
                        inverse.from_ = other.to
                        inverse.to = other.from_
                        con.append(inverse)
                else:
                    # if no relation exists
                    universe = RCCConstraint(*self._create_all_rcc_relation())
                    universe.from_ = self._get_variable_by_id[i]
                    universe.to = self._get_variable_by_id[j]
                    con.append(universe)
            rcc_rels.append(con)
        return rcc_rels

    def _create_all_rcc_relation(self) -> list[RCCConstraint.Type]:
        return list(RCCConstraint.Type)

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(Region(self, self._ids))
            self._ids += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def register_value_choice_functions(self) -> None:
        pass
