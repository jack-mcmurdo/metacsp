"""Port of spatial/geometry/RCC2ConstraintSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.spatial.geometry.geometric_constraint import GeometricConstraint
from metacsp.spatial.geometry.polygon import Polygon

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["RCC2ConstraintSolver"]


class RCC2ConstraintSolver(ConstraintSolver):
    def __init__(self) -> None:
        super().__init__([GeometricConstraint], Polygon)
        self.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)

    def propagate(self) -> bool:
        vars_ = self.constraint_network.get_variables()
        for k in range(len(vars_)):
            for i in range(len(vars_)):
                if i == k:
                    continue
                for j in range(len(vars_)):
                    if j == k or j == i:
                        continue
                    r_ij = cast(
                        "GeometricConstraint | None",
                        self.constraint_network.get_constraint(vars_[i], vars_[j]),
                    )
                    if r_ij is None:
                        continue
                    r_ik = cast(
                        "GeometricConstraint | None",
                        self.constraint_network.get_constraint(vars_[i], vars_[k]),
                    )
                    if r_ik is None:
                        continue
                    r_kj = cast(
                        "GeometricConstraint | None",
                        self.constraint_network.get_constraint(vars_[k], vars_[j]),
                    )
                    if r_kj is None:
                        continue
                    comp = self._get_composition(r_ik.type, r_kj.type)
                    if r_ij.type not in comp:
                        return False
        return True

    def _get_composition(
        self, o1: GeometricConstraint.Type, o2: GeometricConstraint.Type
    ) -> list[GeometricConstraint.Type]:
        return GeometricConstraint.TRANSITION_TABLE[o1.value][o2.value]

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(Polygon(self, self._ids))
            self._ids += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def register_value_choice_functions(self) -> None:
        pass

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return True
