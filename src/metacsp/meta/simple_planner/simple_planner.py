"""Port of meta/simplePlanner/SimplePlanner.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.framework.variable_prototype import VariablePrototype
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.variable import Variable
    from metacsp.meta.simple_planner.simple_reusable_resource import SimpleReusableResource

__all__ = ["SimplePlanner"]


class SimplePlanner(MetaConstraintSolver):
    """A MetaConstraintSolver whose single ground solver is an
    ActivityNetworkSolver; a SimpleDomain (and its SimpleReusableResources,
    added as further MetaConstraints) drive hierarchical task planning by
    justifying UNJUSTIFIED Activities."""

    def __init__(self, origin: int, horizon: int, animation_time: int) -> None:
        super().__init__(
            [AllenIntervalConstraint, SymbolicValueConstraint],
            animation_time,
            ActivityNetworkSolver(origin, horizon, 500),
        )

    def pre_backtrack(self) -> None:
        """No-op: SimplePlanner needs no extra bookkeeping before branching."""
        pass

    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        """Remove the Activities instantiated for a retracted resolver, freeing their resource usage."""
        ground_solver = cast(ActivityNetworkSolver, self.constraint_solvers[0])
        activity_to_remove: list[Variable] = []

        for v in meta_value.get_variables():
            if not meta_variable.contains_variable(v):
                if isinstance(v, VariablePrototype):
                    v_real = meta_value.get_substitution(v)
                    if v_real is not None:
                        activity_to_remove.append(v_real)

        sd: SimpleDomain | None = None
        for mcon in self.meta_constraints:
            if isinstance(mcon, SimpleDomain):
                sd = mcon
        assert sd is not None

        for v in activity_to_remove:
            for rr in sd.get_current_reusable_resources_used_by_activity(
                cast(SymbolicVariableActivity, v)
            ):
                rr.remove_usage(cast(SymbolicVariableActivity, v))

        ground_solver.remove_variables(activity_to_remove)

    def add_resolver_sub(
        self,
        current_problematic_constraint_network: ConstraintNetwork,
        possible_operator_constraint_network: ConstraintNetwork,
    ) -> bool:
        """Instantiate real Activities for a resolver's VariablePrototypes and register
        their resource usage. Always returns True."""
        ground_solver = cast(ActivityNetworkSolver, self.constraint_solvers[0])

        # Make real variables from variable prototypes.
        for v in possible_operator_constraint_network.get_variables():
            if isinstance(v, VariablePrototype):
                # Parameters for real instantiation: the first is the
                # component itself, the second is the symbol of the Activity
                # to be instantiated.
                component = cast(str, v.parameters[0])
                symbol = cast(str, v.parameters[1])
                tail_activity = cast(
                    SymbolicVariableActivity, ground_solver.create_variable(component)
                )
                tail_activity.set_symbolic_domain(symbol)
                tail_activity.marking = v.marking
                possible_operator_constraint_network.add_substitution(v, tail_activity)

        # Involve real variables in the constraints.
        for con in list(possible_operator_constraint_network.get_constraints()):
            cloned_constraint = con.clone()
            old_scope = con.scope
            new_scope: list[Variable] = []
            for old_var in old_scope:
                if isinstance(old_var, VariablePrototype):
                    substituted = possible_operator_constraint_network.get_substitution(old_var)
                    assert substituted is not None
                    new_scope.append(substituted)
                else:
                    new_scope.append(old_var)
            cloned_constraint.scope = new_scope
            possible_operator_constraint_network.remove_constraint(con)
            possible_operator_constraint_network.add_constraint(cloned_constraint)

        sd = None
        for mcon in self.meta_constraints:
            if isinstance(mcon, SimpleDomain):
                sd = mcon
        assert sd is not None

        # Set resource usage if necessary.
        for v in possible_operator_constraint_network.get_variables():
            for rr in sd.get_current_reusable_resources_used_by_activity(v):
                cast("SimpleReusableResource", rr).set_usage(cast(SymbolicVariableActivity, v))

        return True

    def post_backtrack(self, mv: MetaVariable) -> None:
        """Reset a SimpleDomain flaw's Activities to UNJUSTIFIED after backtracking over it."""
        if isinstance(mv.meta_constraint, SimpleDomain):
            assert mv.constraint_network is not None
            for v in mv.constraint_network.get_variables():
                v.marking = SimpleDomain.markings.UNJUSTIFIED

    def get_upper_bound(self) -> float:
        """Always 0.0: SimplePlanner does not support branch-and-bound optimization."""
        return 0.0

    def set_upper_bound(self) -> None:
        """No-op: SimplePlanner does not support branch-and-bound optimization."""
        pass

    def get_lower_bound(self) -> float:
        """Always 0.0: SimplePlanner does not support branch-and-bound optimization."""
        return 0.0

    def set_lower_bound(self) -> None:
        """No-op: SimplePlanner does not support branch-and-bound optimization."""
        pass

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        """Always False: SimplePlanner does not support branch-and-bound optimization."""
        return False

    def reset_false_clause(self) -> None:
        """No-op: SimplePlanner does not support branch-and-bound optimization."""
        pass
