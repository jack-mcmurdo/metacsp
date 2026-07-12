"""Port of meta/hybridPlanner/SensingSchedulable.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver import SpatialFluentSolver

__all__ = ["SensingSchedulable"]


class SensingSchedulable(MetaConstraint):
    """A MetaConstraint that pairwise-orders sensing activities (activities
    whose symbol contains ``"sens"``) that overlap in time, without actually
    requiring the (not-yet-ported, M19) runtime sensing machinery -- it only
    inspects a :class:`~metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver.SpatialFluentSolver`'s
    ground activity-network variables."""

    def __init__(self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None) -> None:
        super().__init__(var_oh, val_oh)
        self.before_parameter = 1

    def _binary_peak_collection(
        self, activities: list[SymbolicVariableActivity]
    ) -> list[ConstraintNetwork]:
        ret: list[ConstraintNetwork] = []
        if activities:
            self.logger.debug("Doing binary peak collection with %d activities...", len(activities))
            ground_vars = list(activities)
            for i in range(len(ground_vars) - 1):
                for j in range(i + 1, len(ground_vars)):
                    bi = Bounds(
                        ground_vars[i].temporal_variable.est, ground_vars[i].temporal_variable.eet
                    )
                    bj = Bounds(
                        ground_vars[j].temporal_variable.est, ground_vars[j].temporal_variable.eet
                    )
                    if bi.intersect_strict(bj) is not None:
                        cn = ConstraintNetwork(None)
                        cn.add_variable(ground_vars[i])
                        cn.add_variable(ground_vars[j])
                        ret.append(cn)
            if ret:
                return ret
        return []

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        assert self.meta_cs is not None
        spatial_fluent_solver = cast("SpatialFluentSolver", self.meta_cs.constraint_solvers[0])
        activity_solver = spatial_fluent_solver.constraint_solvers[1]
        activities: list[SymbolicVariableActivity] = []
        for act in activity_solver.get_variables():
            act = cast("SymbolicVariableActivity", act)
            if "sens" in act.symbolic_variable.symbols[0]:
                activities.append(act)
        return self._binary_peak_collection(activities)

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        conflict = meta_variable.constraint_network
        assert conflict is not None
        # We know this is the result of a binary conflict, so it is safe not
        # to enumerate all resolvers, and hard-coded.
        assert self.meta_cs is not None
        spatial_fluent_solver = cast("SpatialFluentSolver", self.meta_cs.constraint_solvers[0])
        activity_solver = spatial_fluent_solver.constraint_solvers[1]
        ret: list[ConstraintNetwork] = []

        var0 = cast("SymbolicVariableActivity", conflict.get_variables()[0])
        var1 = cast("SymbolicVariableActivity", conflict.get_variables()[1])

        before01 = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Before, Bounds(self.before_parameter, APSPSolver.INF)
        )
        before01.from_ = var0
        before01.to = var1
        resolver0 = ConstraintNetwork(activity_solver)
        resolver0.add_variable(var0)
        resolver0.add_variable(var1)
        resolver0.add_constraint(before01)
        ret.append(resolver0)

        before10 = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Before, Bounds(self.before_parameter, APSPSolver.INF)
        )
        before10.from_ = var1
        before10.to = var0
        resolver1 = ConstraintNetwork(activity_solver)
        resolver1.add_variable(var1)
        resolver1.add_variable(var0)
        resolver1.add_constraint(before10)
        ret.append(resolver1)

        return ret

    def mark_resolved_sub(self, meta_variable: MetaVariable, meta_value: ConstraintNetwork) -> None:
        pass

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def get_ground_solver(self) -> ConstraintSolver:
        assert self.meta_cs is not None
        return cast("ConstraintSolver", self.meta_cs.constraint_solvers[0])

    def __str__(self) -> str:
        return "None"

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> SensingSchedulable | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False
