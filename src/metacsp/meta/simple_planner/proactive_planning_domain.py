"""Port of meta/simplePlanner/ProactivePlanningDomain.java.

The Java example classes that drive this domain (``TestProactivePlanning``,
``TestProactivePlanningAndDispatching``) depend on M19 sensing classes and
are out of scope for this milestone; only the domain class itself is ported
here, per the porting plan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.variable_prototype import VariablePrototype
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.framework.meta.meta_variable import MetaVariable

__all__ = ["ProactivePlanningDomain"]


class ProactivePlanningDomain(SimpleDomain):
    """A SimpleDomain that additionally generates "context inference"
    MetaVariables: at most once per :meth:`reset_context_inference` cycle, a
    null MetaVariable is produced whose values are hypotheses about which
    context-variable state currently holds (one VariablePrototype per
    PlanningOperator head on a ContextVariable component)."""

    def __init__(
        self, capacities: list[int], resource_names: list[str], domain_name: str, everything: str
    ) -> None:
        super().__init__(capacities, resource_names, domain_name, everything)
        self.triggered = False
        self.old_inferences: dict[str, SymbolicVariableActivity] = {}
        self.time_now = -1

    def set_old_inference(self, component: str, old_inf: SymbolicVariableActivity) -> None:
        """Record the last inferred activity for a context-variable component."""
        self.old_inferences[component] = old_inf

    def _generate_goals(self) -> list[VariablePrototype]:
        assert self.meta_cs is not None
        ground_solver = cast(ActivityNetworkSolver, self.meta_cs.constraint_solvers[0])
        ops = self.operators
        vars_: dict[VariablePrototype, None] = {}
        for op in ops:
            head = op.head
            head_component = head[: head.index("::")]
            head_value = head[head.index("::") + 2 :]
            if self.is_context_var(head_component):
                to_infer = VariablePrototype(ground_solver, head_component, head_value, "Inference")
                to_infer.marking = SimpleDomain.markings.UNJUSTIFIED
                vars_[to_infer] = None
        return list(vars_)

    def reset_context_inference(self) -> None:
        """Allow one more context-inference MetaVariable to be produced this cycle."""
        self.triggered = False

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        """The usual planning flaws, plus (at most once per cycle) a context-inference flaw."""
        # Add the normal metavariables for planning (UNJUSTIFIED activities).
        ret = super().get_meta_variables()
        new_ret: list[ConstraintNetwork] = list(ret)
        if not self.triggered:
            self.triggered = True
            # Add a null constraint network to signal that context inference
            # should be done.
            new_ret.append(ConstraintNetwork(None))
        return new_ret

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        """Resolvers for a planning flaw as usual, or hypothesized context states
        for a context-inference flaw."""
        mv = meta_variable.constraint_network
        assert mv is not None

        # If this is not context inference, get metavalues as usual.
        if mv.get_constraints() or mv.get_variables():
            ret = super().get_meta_values(meta_variable)
            if ret:
                # If this is an actuator, add timeNow release to activity
                # representing the metavariable.
                flaw = mv.get_variables()[0]
                if self.is_actuator(flaw.component):
                    release = AllenIntervalConstraint(
                        AllenIntervalConstraint.Type.Release, Bounds(self.time_now, APSPSolver.INF)
                    )
                    release.from_ = flaw
                    release.to = flaw
                    for cn in ret:
                        cn.add_constraint(release)
            return ret

        # We have a context inference metavariable - let's generate all
        # possible worlds.
        possible_goals = self._generate_goals()
        ret_list: list[ConstraintNetwork] = []
        for one_goal in possible_goals:
            cn = ConstraintNetwork(None)
            cn.add_variable(one_goal)
            old_inf = self.old_inferences.get(cast(str, one_goal.parameters[0]))
            skip = False
            # Do not re-infer the last thing that was inferred (prevents
            # having to "model" impossibility to infer something
            # continuously as temporal constraints in the domain).
            if old_inf is not None:
                if old_inf.symbolic_variable.symbols[0] == one_goal.parameters[1]:
                    skip = True
                    self.logger.debug("Skipping %s because of %s", one_goal.parameters[1], old_inf)
                else:
                    before = AllenIntervalConstraint(AllenIntervalConstraint.Type.Before)
                    before.from_ = old_inf
                    before.to = one_goal
                    cn.add_constraint(before)
            if not skip:
                ret_list.append(cn)
        return ret_list

    def update_time_now(self, time_now: int) -> None:
        """Set the current time, used to release actuator activities no earlier than now."""
        self.time_now = time_now
