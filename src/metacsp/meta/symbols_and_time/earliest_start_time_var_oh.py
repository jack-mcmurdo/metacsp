"""Port of meta/symbolsAndTime/EarliestStartTimeVarOH.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, cast

from metacsp.framework.variable_ordering_h import VariableOrderingH
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork

__all__ = ["EarliestStartTimeVarOH"]


class EarliestStartTimeVarOH(VariableOrderingH):
    """Orders MetaVariables by increasing earliest start time (EST) of
    their (single) Activity."""

    def compare(self, n1: ConstraintNetwork, n2: ConstraintNetwork) -> int:
        time1 = cast(SymbolicVariableActivity, n1.get_variables()[0]).temporal_variable.est
        time2 = cast(SymbolicVariableActivity, n2.get_variables()[0]).temporal_variable.est
        if time1 > time2:
            return 1
        if time1 < time2:
            return -1
        return 0

    def collect_data(self, all_meta_variables: Sequence[ConstraintNetwork]) -> None:
        pass
