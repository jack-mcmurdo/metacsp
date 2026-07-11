"""Port of framework/meta/MultiMetaConstraint.java."""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from metacsp.framework.meta.meta_constraint import MetaConstraint

if TYPE_CHECKING:
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_ordering_h import ConstraintOrderingH
    from metacsp.framework.value_ordering_h import ValueOrderingH
    from metacsp.framework.variable_ordering_h import VariableOrderingH

__all__ = ["MultiMetaConstraint"]


class MultiMetaConstraint(MetaConstraint):
    """A MetaConstraint that aggregates several sub-MetaConstraints, picking
    the highest-priority meta-variable amongst them via a ConstraintOrderingH."""

    def __init__(
        self,
        var_oh: VariableOrderingH | None,
        val_oh: ValueOrderingH | None,
        cons_oh: ConstraintOrderingH,
        *metacons: MetaConstraint,
    ) -> None:
        super().__init__(var_oh, val_oh)
        self.my_meta_cons = metacons
        self.my_constraint_ordering_h = cons_oh

    def get_con_ordering_h(self) -> ConstraintOrderingH:
        return self.my_constraint_ordering_h

    def get_meta_variable(self) -> ConstraintNetwork | None:
        sub_meta_cons: dict[MetaConstraint, ConstraintNetwork] = {}
        for mc in self.my_meta_cons:
            new_mv = mc.get_meta_variable()
            if new_mv is not None:
                sub_meta_cons[mc] = new_mv

        mcs = sorted(
            sub_meta_cons.keys(), key=functools.cmp_to_key(self.get_con_ordering_h().compare)
        )
        return sub_meta_cons[mcs[0]]
