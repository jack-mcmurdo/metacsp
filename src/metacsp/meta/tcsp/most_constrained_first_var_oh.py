"""Port of meta/TCSP/MostConstrainedFirstVarOH.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, cast

from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.multi.tcsp.distance_constraint import DistanceConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork

__all__ = ["MostConstrainedFirstVarOH"]


class MostConstrainedFirstVarOH(VariableOrderingH):
    """Orders TCSP MetaVariables by the number of disjuncts in their
    DistanceConstraint (fewest disjuncts -- i.e. most constrained -- first)."""

    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        dc0 = cast(DistanceConstraint, n1.get_constraints()[0])
        dc1 = cast(DistanceConstraint, n2.get_constraints()[0])
        return len(dc0.internal_constraints or []) - len(dc1.internal_constraints or [])

    def collect_data(self, all_meta_variables: Sequence[ConstraintNetwork]) -> None:
        pass
