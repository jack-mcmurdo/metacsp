"""Port of meta/hybridPlanner/MetaOccupiedConstraint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.framework.variable_prototype import VariablePrototype
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.multi.allen_interval.allen_interval import AllenInterval
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra.bounding_box import BoundingBox
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable import Variable
    from metacsp.framework.variable_ordering_h import VariableOrderingH
    from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.multi.temporal_rectangle_algebra.spatial_fluent import SpatialFluent
    from metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver import SpatialFluentSolver

__all__ = ["MetaOccupiedConstraint"]


class MetaOccupiedConstraint(MetaConstraint):
    """A MetaConstraint flagging pairs of (movable) SpatialFluents whose
    bounding boxes spatially overlap while their activities also overlap in
    time, and resolving the conflict by temporally ordering them (Before, in
    either direction) -- or, if the "free arm" heuristic is active, by
    inserting a new subgoal moving one of the objects out of the way."""

    def __init__(self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None) -> None:
        super().__init__(var_oh, val_oh)
        self.pad = 0
        self._free_arm_heuristic = False
        self.before_parameter = 1

    def active_heuristic(self, active: bool) -> None:
        self._free_arm_heuristic = active

    def set_pad(self, pad: int) -> None:
        self.pad = pad

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        activity_to_fluent: dict[SymbolicVariableActivity, SpatialFluent] = {}
        ground_solver = cast("SpatialFluentSolver", self.get_ground_solver())
        for var in ground_solver.get_variables():
            fluent = cast("SpatialFluent", var)
            if fluent.rectangular_region.ontological_prop.is_movable:
                activity_to_fluent[fluent.activity] = fluent
        return self._binary_peak_collection(activity_to_fluent)

    def _binary_peak_collection(
        self, a_to_sf: dict[SymbolicVariableActivity, SpatialFluent]
    ) -> list[ConstraintNetwork]:
        activities = list(a_to_sf.keys())
        ret: list[ConstraintNetwork] = []
        if activities:
            self.logger.debug("Doing binary peak collection with %d activities...", len(activities))
            ground_vars = activities
            for a in ground_vars:
                if self.is_conflicting([a], a_to_sf):
                    cn = ConstraintNetwork(None)
                    cn.add_variable(a)
                    ret.append(cn)
            if ret:
                return ret
            for i in range(len(ground_vars) - 1):
                for j in range(i + 1, len(ground_vars)):
                    bi = Bounds(
                        ground_vars[i].temporal_variable.est, ground_vars[i].temporal_variable.eet
                    )
                    bj = Bounds(
                        ground_vars[j].temporal_variable.est, ground_vars[j].temporal_variable.eet
                    )
                    if bi.intersect_strict(bj) is not None and self.is_conflicting(
                        [ground_vars[i], ground_vars[j]], a_to_sf
                    ):
                        cn = ConstraintNetwork(None)
                        cn.add_variable(ground_vars[i])
                        cn.add_variable(ground_vars[j])
                        ret.append(cn)
            if ret:
                return ret
        return []

    def is_conflicting(
        self,
        peak: list[SymbolicVariableActivity],
        activity_to_fluent: dict[SymbolicVariableActivity, SpatialFluent],
    ) -> bool:
        if len(peak) == 1:
            return False
        for act in peak:
            if "manipulationArea" in act.symbolic_variable.symbols[0]:
                return False

        self.logger.debug("_________________________________________________")
        for act in peak:
            self.logger.debug("peak: %s", activity_to_fluent.get(act))
        self.logger.debug("_________________________________________________")

        unboundedsf: list[SpatialFluent] = []
        boundedsf: list[SpatialFluent] = []
        # This distinguishes objects that are unbounded (in the past, moved,
        # so a new SpatialFluent was generated and the previous one became
        # spatially unbounded) from bounded (future/current) objects.
        for act in peak:
            fluent = activity_to_fluent[act]
            rr = fluent.rectangular_region
            interval_x = cast(AllenInterval, rr.internal_variables[0])
            interval_y = cast(AllenInterval, rr.internal_variables[1])
            if self._is_unbounded_bounding_box(
                Bounds(interval_x.est, interval_x.lst),
                Bounds(interval_x.eet, interval_x.let),
                Bounds(interval_y.est, interval_y.lst),
                Bounds(interval_y.eet, interval_y.let),
            ):
                unboundedsf.append(fluent)
            else:
                boundedsf.append(fluent)

        if not unboundedsf or not boundedsf:
            return False

        if unboundedsf[-1].name == boundedsf[-1].name:
            return False

        rec1 = _bounding_box_of(boundedsf[0]).get_almost_centre_rectangle()

        from metacsp.meta.hybrid_planner.simple_hybrid_planner import SimpleHybridPlanner

        rec2 = None
        old_rectangular_region = cast(
            SimpleHybridPlanner, self.meta_cs
        ).get_old_rectangular_region()
        for name, bb in old_rectangular_region.items():
            if unboundedsf[0].rectangular_region.name == name:
                rec2 = bb.get_almost_centre_rectangle()

        r1new_x, r1new_y = rec1.min_x - self.pad, rec1.min_y - self.pad
        r1new_w, r1new_h = rec1.width + 2 * self.pad, rec1.height + 2 * self.pad
        r2new_x, r2new_y = rec2.min_x - self.pad, rec2.min_y - self.pad
        r2new_w, r2new_h = rec2.width + 2 * self.pad, rec2.height + 2 * self.pad
        from metacsp.multi.spatial.rectangle_algebra.bounding_box import AwtRectangle

        r1new = AwtRectangle(r1new_x, r1new_y, r1new_w, r1new_h)
        r2new = AwtRectangle(r2new_x, r2new_y, r2new_w, r2new_h)

        if r1new.intersects(r2new):
            return True
        return False

    def _is_unbounded_bounding_box(
        self, x_lb: Bounds, x_ub: Bounds, y_lb: Bounds, y_ub: Bounds
    ) -> bool:
        ground_solver = cast(
            "SpatialFluentSolver", self.meta_cs.constraint_solvers[0]  # type: ignore[union-attr]
        )
        activity_solver = cast("ActivityNetworkSolver", ground_solver.constraint_solvers[1])
        horizon = activity_solver.horizon

        if (
            (x_lb.min == 0 and x_lb.max == horizon)
            and (x_ub.min == 0 and x_ub.max == horizon)
            and (y_lb.min == 0 and y_lb.max == horizon)
            and (y_lb.min == 0 and y_ub.max == horizon)
        ):
            return True
        return False

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        conflict = meta_variable.constraint_network
        assert conflict is not None
        # We know this is the result of a binary conflict, so it is safe not
        # to enumerate all resolvers, and hard-coded.
        ground_solver = cast("SpatialFluentSolver", self.meta_cs.constraint_solvers[0])  # type: ignore[union-attr]
        activity_solver = ground_solver.constraint_solvers[1]
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

        if self._free_arm_heuristic:
            resolver2 = ConstraintNetwork(activity_solver)
            ground_act_solver = cast(
                "ActivityNetworkSolver",
                cast("SpatialFluentSolver", self.get_ground_solver()).constraint_solvers[1],
            )

            problematic_activity: SymbolicVariableActivity | None = None
            for var in conflict.get_variables():
                act = cast("SymbolicVariableActivity", var)
                if act.temporal_variable.est != act.temporal_variable.lst:
                    problematic_activity = act

            d = 2000

            tail_activity = VariablePrototype(ground_act_solver, "atLocation", "at_cup1_tray1()")
            tail_activity.marking = SimpleDomain.markings.UNJUSTIFIED
            resolver2.add_variable(tail_activity)

            duration = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Duration, Bounds(d, APSPSolver.INF)
            )
            duration.from_ = tail_activity
            duration.to = tail_activity
            resolver2.add_constraint(duration)

            before = AllenIntervalConstraint(
                AllenIntervalConstraint.Type.Before,
                *AllenIntervalConstraint.Type.Before.get_default_bounds(),
            )
            before.from_ = tail_activity
            before.to = problematic_activity
            resolver2.add_constraint(before)

            ret.append(resolver2)
            self._free_arm_heuristic = False  # this has to be False! do not change it

        return ret

    def mark_resolved_sub(self, meta_variable: MetaVariable, meta_value: ConstraintNetwork) -> None:
        pass

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def __str__(self) -> str:
        return "MetaOccupiedConstraint"

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> MetaOccupiedConstraint | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def get_ground_solver(self) -> ConstraintSolver:
        return cast("ConstraintSolver", self.meta_cs.constraint_solvers[0])  # type: ignore[union-attr]


def _bounding_box_of(fluent: SpatialFluent) -> BoundingBox:
    rr = fluent.rectangular_region
    interval_x = cast(AllenInterval, rr.internal_variables[0])
    interval_y = cast(AllenInterval, rr.internal_variables[1])
    return BoundingBox(
        Bounds(interval_x.est, interval_x.lst),
        Bounds(interval_x.eet, interval_x.let),
        Bounds(interval_y.est, interval_y.lst),
        Bounds(interval_y.eet, interval_y.let),
    )
