"""Port of framework/multi/MultiDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from metacsp.framework.domain import Domain

if TYPE_CHECKING:
    from metacsp.framework.multi.multi_variable import MultiVariable
    from metacsp.framework.variable import Variable

__all__ = ["MultiDomain"]


class MultiDomain(Domain):
    """A domain composed of many elementary domains; used to represent the
    domains of MultiVariables."""

    def __init__(self, v: MultiVariable, *domains: Domain) -> None:
        super().__init__(v)
        self.domains = domains

    def choose_value(self, vcf: str | None = None) -> Any:
        """It does not make sense to choose one value from a MultiDomain
        (use :meth:`choose_values` instead); always returns None."""
        return None

    def choose_values(self) -> dict[Variable, Any]:
        """Choose values for all internal domains according to their own
        value choice functions."""
        from metacsp.framework.multi.multi_variable import MultiVariable

        mv = self.variable
        assert isinstance(mv, MultiVariable)
        values: dict[Variable, Any] = {}
        for v in mv.internal_variables:
            if isinstance(v, MultiVariable):
                values.update(v.domain.choose_values())
            else:
                values[v] = v.domain.choose_value()
        return values

    def __str__(self) -> str:
        return str(list(self.domains))
