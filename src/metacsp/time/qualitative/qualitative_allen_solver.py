"""Port of time/qualitative/QualitativeAllenSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.time.qualitative.qualitative_allen_interval_constraint import (
    QualitativeAllenIntervalConstraint,
)
from metacsp.time.qualitative.simple_allen_interval import SimpleAllenInterval

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["QualitativeAllenSolver"]

Type = QualitativeAllenIntervalConstraint.Type


class QualitativeAllenSolver(ConstraintSolver):
    """Path-consistency solver for disjunctive (qualitative) Allen interval
    constraints."""

    def __init__(self) -> None:
        super().__init__([QualitativeAllenIntervalConstraint], SimpleAllenInterval)
        self.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)
        self._ids = 0
        self._complete_network: ConstraintNetwork | None = None
        self._successful_propagation = False

    def propagate(self) -> bool:
        """Run path consistency over the completed constraint network; False if inconsistent."""
        if not self.get_constraints():
            return True
        self._create_complete_network()
        self._successful_propagation = self._path_consistency()
        return self._successful_propagation

    @property
    def constraint_network(self) -> ConstraintNetwork:
        """The completed (all-pairs) network after a successful propagation, else the raw one."""
        if self._successful_propagation:
            assert self._complete_network is not None
            return self._complete_network
        return self.the_network

    @constraint_network.setter
    def constraint_network(self, new_cn: ConstraintNetwork) -> None:
        """Replace this solver's raw ConstraintNetwork."""
        self.the_network = new_cn

    def _create_complete_network(self) -> None:
        self._complete_network = ConstraintNetwork(self)
        original_network = self.the_network
        for var in original_network.get_variables():
            self._complete_network.add_variable(var)
        for con in original_network.get_constraints():
            self._complete_network.add_constraint(con)
        vars_ = self._complete_network.get_variables()
        for i, vi in enumerate(vars_):
            for j, vj in enumerate(vars_):
                if i != j and original_network.get_constraint(vi, vj) is None:
                    if original_network.get_constraint(vj, vi) is not None:
                        existing = cast(
                            QualitativeAllenIntervalConstraint,
                            original_network.get_constraint(vj, vi),
                        )
                        inverses = QualitativeAllenIntervalConstraint.get_inverse_relation(
                            existing.types
                        )
                        inverse = QualitativeAllenIntervalConstraint(*inverses)
                        inverse.from_ = vi
                        inverse.to = vj
                        self._complete_network.add_constraint(inverse)
                    else:
                        universe = QualitativeAllenIntervalConstraint(*Type)
                        universe.from_ = vi
                        universe.to = vj
                        self._complete_network.add_constraint(universe)

    def _path_consistency(self) -> bool:
        assert self._complete_network is not None
        fixedpoint = False
        vars_ = self._complete_network.get_variables()
        while not fixedpoint:
            fixedpoint = True
            for k in range(len(vars_)):
                for i in range(len(vars_)):
                    if i == k:
                        continue
                    for j in range(len(vars_)):
                        if j == k or j == i:
                            continue
                        r_ij = cast(
                            QualitativeAllenIntervalConstraint,
                            self._complete_network.get_constraint(vars_[i], vars_[j]),
                        )
                        r_ik = cast(
                            QualitativeAllenIntervalConstraint,
                            self._complete_network.get_constraint(vars_[i], vars_[k]),
                        )
                        r_kj = cast(
                            QualitativeAllenIntervalConstraint,
                            self._complete_network.get_constraint(vars_[k], vars_[j]),
                        )
                        comp = self._get_composition(r_ik, r_kj)
                        inters = self._get_intersection(r_ij, comp)
                        if not inters.types:
                            return False
                        if len(inters.types) < len(r_ij.types):
                            self._complete_network.remove_constraint(r_ij)
                            self._complete_network.add_constraint(inters)
                            fixedpoint = False
        return True

    @staticmethod
    def _get_intersection(
        o1: QualitativeAllenIntervalConstraint, o2: QualitativeAllenIntervalConstraint
    ) -> QualitativeAllenIntervalConstraint:
        intersection = [t for t in o1.types if t in o2.types]
        ret = QualitativeAllenIntervalConstraint(*intersection)
        ret.from_ = o1.from_
        ret.to = o1.to
        return ret

    @staticmethod
    def _get_composition(
        o1: QualitativeAllenIntervalConstraint, o2: QualitativeAllenIntervalConstraint
    ) -> QualitativeAllenIntervalConstraint:
        cmp_relation: list[Type] = []
        for t1 in o1.types:
            for t2 in o2.types:
                for t3 in QualitativeAllenIntervalConstraint.TRANSITION_TABLE[t1.value][t2.value]:
                    if t3 not in cmp_relation:
                        cmp_relation.append(t3)
        ret = QualitativeAllenIntervalConstraint(*cmp_relation)
        ret.from_ = o1.from_
        ret.to = o2.to
        return ret

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        """No-op: constraints are only used when :meth:`propagate` next runs."""
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        """No-op: constraints are only used when :meth:`propagate` next runs."""
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        """Create ``num`` SimpleAllenInterval variables."""
        ret = []
        for _ in range(num):
            ret.append(SimpleAllenInterval(self, self._ids))
            self._ids += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        """No-op: nothing to release for a SimpleAllenInterval."""
        pass

    def register_value_choice_functions(self) -> None:
        """No-op: this solver's Domain has no value choice functions."""
        pass
