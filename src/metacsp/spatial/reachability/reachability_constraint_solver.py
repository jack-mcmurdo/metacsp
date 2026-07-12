"""Port of spatial/reachability/ReachabilityContraintSolver.java.

Named ``ReachabilityConstraintSolver`` here, correcting the Java source's
upstream "Contraint" typo (file ``ReachabilityContraintSolver.java``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.spatial.reachability.configuration_variable import ConfigurationVariable
from metacsp.spatial.reachability.reachability_constraint import ReachabilityConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["ReachabilityConstraintSolver"]


class ReachabilityConstraintSolver(ConstraintSolver):
    def __init__(self) -> None:
        super().__init__([ReachabilityConstraint], ConfigurationVariable)
        # Java leaves AUTO_PROPAGATE commented out -- solver stays MANUAL_PROPAGATE.

    def propagate(self) -> bool:
        return True

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(ConfigurationVariable(self, self._ids))
            self._ids += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def register_value_choice_functions(self) -> None:
        pass
