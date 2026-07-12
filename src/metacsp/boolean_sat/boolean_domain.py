"""Port of booleanSAT/BooleanDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain

if TYPE_CHECKING:
    from metacsp.boolean_sat.boolean_variable import BooleanVariable

__all__ = ["BooleanDomain"]


class BooleanDomain(Domain):
    """The domain of a BooleanVariable: the set {T,F}.

    ValueChoiceFunctions for this domain are dynamically managed by
    BooleanSatisfiabilitySolver, which guarantees a ValueChoiceFunction named
    "modelX" for each model X in {0 ... maxModels-1} of the current
    ConstraintNetwork. The network is never left in an inconsistent state, so
    "model0" is always defined.
    """

    def __init__(self, v: BooleanVariable, *values: bool) -> None:
        super().__init__(v)
        if values:
            if len(values) != 2:
                raise ValueError(
                    "Invalid values for a Boolean domain (two values must be supplied)"
                )
            self.domain = [values[0], values[1]]
        else:
            self.domain = [True, True]
        self.set_default_value_choice_function("model0")

    def allow_true(self) -> None:
        """Allow True as a value of this domain."""
        self.domain[0] = True

    def allow_false(self) -> None:
        """Allow False as a value of this domain."""
        self.domain[1] = True

    @property
    def can_be_true(self) -> bool:
        """True iff True is currently an allowed value."""
        return self.domain[0]

    @property
    def can_be_false(self) -> bool:
        """True iff False is currently an allowed value."""
        return self.domain[1]

    def compare_to(self, o: object) -> int:
        """Ordering comparison favoring the more constrained (fewer allowed values) domain."""
        if not isinstance(o, BooleanDomain):
            return 0
        counter_this = int(self.domain[0]) + int(self.domain[1])
        counter_that = int(o.domain[0]) + int(o.domain[1])
        return counter_that - counter_this

    def __str__(self) -> str:
        ret = "["
        if self.domain[0] and self.domain[1]:
            ret += "T,F"
        elif self.domain[0] and not self.domain[1]:
            ret += "T"
        elif not self.domain[0] and self.domain[1]:
            ret += "F"
        ret += "]"
        return ret
