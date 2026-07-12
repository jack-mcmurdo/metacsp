"""Port of meta/hybridPlanner/SimpleHybridPlannerInferenceCallback.java.

Java's ``SimpleHybridPlannerInferenceCallback`` implements the single-method
``org.metacsp.sensing.InferenceCallback`` interface (M19, not yet ported).
Per C4, single-method callback interfaces normally become "accept any
Python callable" -- but this class carries state beyond the callback method
itself (``planner``, ``domain``), so -- exactly as M16's
``SimplePlannerInferenceCallback`` -- it is ported as a small class instead,
exposing the same ``do_inference(time_now)`` method Java's
``InferenceCallback.doInference(long)`` requires. Instances of this class
are themselves valid callables for that (still-unported) interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.meta.hybrid_planner._sort_utils import sort_dict_by_value
from metacsp.meta.hybrid_planner.fluent_based_simple_domain import FluentBasedSimpleDomain
from metacsp.meta.hybrid_planner.meta_occupied_constraint import MetaOccupiedConstraint
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.meta.simple_planner.simple_reusable_resource import SimpleReusableResource
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.temporal_rectangle_algebra.spatial_fluent_solver import SpatialFluentSolver
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.meta.hybrid_planner.simple_hybrid_planner import SimpleHybridPlanner
    from metacsp.meta.simple_planner.simple_operator import SimpleOperator
    from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity

__all__ = ["SimpleHybridPlannerInferenceCallback"]


class SimpleHybridPlannerInferenceCallback:
    """Port of ``SimpleHybridPlannerInferenceCallback.java``: on a failed
    replan, cleans up planned-but-stale activities/resource usage from the
    current time forward and, if the planner reports it is
    :meth:`~.simple_hybrid_planner.SimpleHybridPlanner.learning_from_failure`,
    inserts a subgoal freeing up whichever resource is blocking progress."""

    def __init__(self, planner: SimpleHybridPlanner) -> None:
        self.planner: SimpleHybridPlanner | None = planner
        self.logger = get_logger(type(self))
        self.domain: FluentBasedSimpleDomain | None = None
        for mc in planner.meta_constraints:
            if isinstance(mc, FluentBasedSimpleDomain):
                self.domain = mc
                break

    def do_inference(self, time_now: int) -> None:
        if self.planner is None:
            return
        assert self.domain is not None
        planner = self.planner
        self.domain.update_time_now(time_now)

        if not planner.backtrack():
            self.logger.info("Time now: %d", time_now)
            planner.operators_along_branch.clear()
            constraint_domain_has_to_be_removed: list[SymbolicVariableActivity] = []
            acts_to_be_removed: list[SymbolicVariableActivity] = []
            current_situation: list[SymbolicVariableActivity] = []

            for cn in list(planner.resolvers.keys()):
                for goal in planner.get_goals():
                    meta_var_act = cast("SymbolicVariableActivity", cn.get_variables()[0])
                    if meta_var_act == goal:
                        meta_var_act.marking = SimpleDomain.markings.UNJUSTIFIED
                        constraint_domain_has_to_be_removed.append(meta_var_act)
                    elif meta_var_act.temporal_variable.lst >= time_now - 1:
                        constraint_domain_has_to_be_removed.append(meta_var_act)
                        acts_to_be_removed.append(meta_var_act)
                    elif meta_var_act.temporal_variable.eet > time_now:
                        current_situation.append(meta_var_act)

            ground_act_solver = cast(
                "ActivityNetworkSolver",
                cast(SpatialFluentSolver, planner.constraint_solvers[0]).constraint_solvers[1],
            )
            cons_to_be_removed: list[Constraint] = []
            for con in ground_act_solver.get_constraints():
                for act in constraint_domain_has_to_be_removed:
                    if con.scope[0] == act or con.scope[1] == act:
                        cons_to_be_removed.append(con)
                        break
            ground_act_solver.remove_constraints(cons_to_be_removed)

            activity_on_resource_use: list[SymbolicVariableActivity] = []
            for mc in planner.meta_constraints:
                if isinstance(mc, SimpleReusableResource):
                    for act in mc.activity_on_use or []:
                        activity_on_resource_use.append(
                            cast("SymbolicVariableActivity", act.variable)
                        )

            for mc in planner.meta_constraints:
                if isinstance(mc, FluentBasedSimpleDomain):
                    for v in activity_on_resource_use:
                        for rr in mc.get_current_reusable_resources_used_by_activity(v):
                            rr.remove_usage(v)

            ground_act_solver.remove_variables(acts_to_be_removed)

            causal_reasoner: FluentBasedSimpleDomain | None = None
            for mc in planner.meta_constraints:
                if isinstance(mc, FluentBasedSimpleDomain):
                    causal_reasoner = mc
                    causal_reasoner.reset_all_resource_allocation()
                    break
            planner.clear_resolvers()

            for mc in planner.meta_constraints:
                if isinstance(mc, MetaOccupiedConstraint):
                    break

            if planner.learning_from_failure():
                # Get overlapped objects.
                overlapped_object: list[str] = []

                alternative_operators: dict[SymbolicVariableActivity, list[SimpleOperator]] = {}
                assert causal_reasoner is not None
                for act in current_situation:
                    if act.component == "RobotProprioception":
                        ops: list[SimpleOperator] = []
                        for op in causal_reasoner.operators:
                            head = f"{act.component}::{act.symbolic_variable.symbols[0]}"
                            if op.head == head:
                                assert op.requirement_activities is not None
                                for candidate in causal_reasoner.operators:
                                    if candidate.head == op.requirement_activities[0]:
                                        ops.append(candidate)
                        alternative_operators[act] = ops

                best_applicable_operator = self._get_best_expansion(
                    current_situation, alternative_operators, overlapped_object
                )
                assert best_applicable_operator.requirement_activities is not None
                for operator_head in best_applicable_operator.requirement_activities:
                    opeator_head_component = operator_head[: operator_head.index("::")]
                    operator_head_symbol = operator_head[operator_head.index("::") + 2 :]

                    if opeator_head_component == "atLocation":
                        cons: list[Constraint] = []
                        duration = 1000
                        spatial_fluent_solver = cast(
                            SpatialFluentSolver, planner.constraint_solvers[0]
                        )
                        activity_solver = spatial_fluent_solver.constraint_solvers[1]
                        two = cast(
                            "SymbolicVariableActivity",
                            activity_solver.create_variable(opeator_head_component),
                        )
                        two.set_symbolic_domain(operator_head_symbol)
                        two.marking = SimpleDomain.markings.UNJUSTIFIED

                        duration_holding = AllenIntervalConstraint(
                            AllenIntervalConstraint.Type.Duration, Bounds(duration, APSPSolver.INF)
                        )
                        duration_holding.from_ = two
                        duration_holding.to = two
                        cons.append(duration_holding)

                        before = AllenIntervalConstraint(
                            AllenIntervalConstraint.Type.Before,
                            *AllenIntervalConstraint.Type.Before.get_default_bounds(),
                        )
                        before.from_ = two
                        before.to = planner.get_goals()[0]
                        cons.append(before)

                        activity_solver.add_constraints(*cons)

    def _get_best_expansion(
        self,
        current_situation: list[SymbolicVariableActivity],
        alternative_operators: dict[SymbolicVariableActivity, list[SimpleOperator]],
        overlapped_object: list[str],
    ) -> SimpleOperator:
        rank: dict[SimpleOperator, int] = {}
        for ops in alternative_operators.values():
            for op in ops:
                assert op.requirement_activities is not None
                rank[op] = len(op.requirement_activities)
        sorted_rank = sort_dict_by_value(rank)
        return next(iter(sorted_rank))
