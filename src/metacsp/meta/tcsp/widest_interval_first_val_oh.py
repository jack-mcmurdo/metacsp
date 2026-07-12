"""Port of meta/TCSP/WidestIntervalFirstValOH.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.multi.tcsp.distance_constraint import DistanceConstraint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.simple_distance_constraint import SimpleDistanceConstraint
from metacsp.framework.value_ordering_h import ValueOrderingH

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork

__all__ = ["WidestIntervalFirstValOH"]

_INT_MAX = 2**31 - 1


class WidestIntervalFirstValOH(ValueOrderingH):
    """Orders TCSP meta values (single-disjunct DistanceConstraints) by
    decreasing interval width -- widest (most flexible) first."""

    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        """Negative/zero/positive as ``n1``'s disjunct is wider/equal/narrower than ``n2``'s."""
        cons0 = n1.get_constraints()
        cons1 = n2.get_constraints()
        con0 = cast(SimpleDistanceConstraint, cast(DistanceConstraint, cons0[0]).internal_constraints[0])  # type: ignore[index]
        con1 = cast(SimpleDistanceConstraint, cast(DistanceConstraint, cons1[0]).internal_constraints[0])  # type: ignore[index]

        min0 = _INT_MAX if con0.minimum == APSPSolver.INF else int(con0.minimum)
        max0 = _INT_MAX if con0.maximum == APSPSolver.INF else int(con0.maximum)
        min1 = _INT_MAX if con1.minimum == APSPSolver.INF else int(con1.minimum)
        max1 = _INT_MAX if con1.maximum == APSPSolver.INF else int(con1.maximum)

        distance0 = abs(max0 - min0)
        distance1 = abs(max1 - min1)
        return distance0 - distance1
