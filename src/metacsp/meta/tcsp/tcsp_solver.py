"""Port of meta/TCSP/TCSPSolver.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.tcsp.distance_constraint import DistanceConstraint
from metacsp.multi.tcsp.distance_constraint_solver import DistanceConstraintSolver

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.multi.multi_constraint import MultiConstraint

__all__ = ["TCSPSolver"]


class TCSPSolver(MetaConstraintSolver):
    """A MetaConstraintSolver whose single ground solver is a
    DistanceConstraintSolver (TCSP): solves disjunctive temporal problems by
    committing each disjunctive DistanceConstraint to one disjunct at a time."""

    def __init__(self, origin: int, horizon: int, animation_time: int = 0) -> None:
        super().__init__(
            [DistanceConstraint], animation_time, DistanceConstraintSolver(origin, horizon)
        )

    def pre_backtrack(self) -> None:
        cs = cast(MultiConstraintSolver, self.constraint_solvers[0])
        cs.set_options(MultiConstraintSolver.Options.FORCE_CONSISTENCY)

    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        dc = cast("MultiConstraint", meta_variable.get_constraints()[0])
        dc.set_propagate_later()

    def add_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> bool:
        dc = cast("MultiConstraint", meta_value.get_constraints()[0])
        dc.set_propagate_immediately()
        return True

    def post_backtrack(self, mv: MetaVariable) -> None:
        pass

    def get_upper_bound(self) -> float:
        return 0.0

    def set_upper_bound(self) -> None:
        pass

    def get_lower_bound(self) -> float:
        return 0.0

    def set_lower_bound(self) -> None:
        pass

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        return False

    def reset_false_clause(self) -> None:
        pass
