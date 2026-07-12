"""Port of meta/TCSP/TCSPLabeling.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.framework.multi.multi_constraint import MultiConstraint
from metacsp.multi.tcsp.distance_constraint import DistanceConstraint
from metacsp.time.bounds import Bounds
from metacsp.time.simple_distance_constraint import SimpleDistanceConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH

__all__ = ["TCSPLabeling"]


class TCSPLabeling(MetaConstraint):
    """A MetaConstraint that finds disjunctive DistanceConstraints not yet
    committed to a single disjunct and offers one meta value per disjunct
    (labeling the TCSP)."""

    def __init__(self, var_oh: VariableOrderingH | None, val_oh: ValueOrderingH | None) -> None:
        super().__init__(var_oh, val_oh)

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        dcn = self.get_ground_solver().constraint_network
        ret: list[ConstraintNetwork] = []
        for con in dcn.get_constraints():
            dc = cast(DistanceConstraint, con)
            # Only get variables representing constraints that are not propagated.
            if not dc.propagate_immediately():
                one_edge = ConstraintNetwork(dc.from_.constraint_solver)
                one_edge.add_variable(dc.from_)
                one_edge.add_variable(dc.to)
                one_edge.add_constraint(dc)
                ret.append(one_edge)
        return ret

    def get_meta_values(self, meta_variable: MetaVariable) -> list[ConstraintNetwork]:
        conflict = meta_variable.constraint_network
        assert conflict is not None
        cons = conflict.get_constraints()
        first = cast(DistanceConstraint, cons[0])
        internal_constraints = first.internal_constraints
        assert internal_constraints is not None
        from_ = first.from_
        to = first.to
        ground_solver = self.get_ground_solver()
        dcs: list[ConstraintNetwork] = []
        for internal in internal_constraints:
            sdc = cast(SimpleDistanceConstraint, internal)
            interval = Bounds(sdc.minimum, sdc.maximum)
            dc = DistanceConstraint(interval)
            dc.from_ = from_
            dc.to = to
            dcn = ConstraintNetwork(ground_solver)
            dcn.add_variable(from_)
            dcn.add_variable(to)
            dcn.add_constraint(dc)
            dcs.append(dcn)
        return dcs

    def __str__(self) -> str:
        return type(self).__name__

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def mark_resolved_sub(self, con: MetaVariable, meta_value: ConstraintNetwork) -> None:
        assert con.constraint_network is not None
        dcs = con.constraint_network.get_constraints()
        mc = cast(MultiConstraint, dcs[0])
        mc.set_propagate_immediately()

    @property
    def edge_label(self) -> str | None:
        return None

    def clone(self) -> TCSPLabeling | None:
        return None

    def is_equivalent(self, c: Constraint) -> bool:
        return False

    def get_ground_solver(self) -> ConstraintSolver:
        assert self.meta_cs is not None
        return self.meta_cs.constraint_solvers[0]
