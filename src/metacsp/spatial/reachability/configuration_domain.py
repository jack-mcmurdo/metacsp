"""Port of spatial/reachability/ConfigurationDomain.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain

if TYPE_CHECKING:
    from metacsp.spatial.reachability.configuration_variable import ConfigurationVariable

__all__ = ["ConfigurationDomain"]


class ConfigurationDomain(Domain):
    def __init__(self, cv: ConfigurationVariable) -> None:
        super().__init__(cv)
        self.configuration_name = f"Interval{cv.id}"

    def compare_to(self, other: object) -> int:
        if isinstance(other, ConfigurationDomain):
            return (self.configuration_name > other.configuration_name) - (
                self.configuration_name < other.configuration_name
            )
        return 0

    def __str__(self) -> str:
        return self.configuration_name

    def __eq__(self, other: object) -> bool:
        """Compares two time intervals, returning true iff their start and
        end times coincide."""
        return (
            isinstance(other, ConfigurationDomain)
            and self.configuration_name == other.configuration_name
        )

    def __hash__(self) -> int:
        return hash(self.configuration_name)
