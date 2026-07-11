"""Port of time/qualitative/SimpleInterval.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain

if TYPE_CHECKING:
    from metacsp.time.qualitative.simple_allen_interval import SimpleAllenInterval

__all__ = ["SimpleInterval"]


class SimpleInterval(Domain):
    """Represents intervals of time without metric extension.

    Used as a domain for SimpleAllenInterval.
    """

    def __init__(self, sai: SimpleAllenInterval) -> None:
        super().__init__(sai)
        self.interval_name = f"Interval{sai.id}"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SimpleInterval) and self.interval_name == other.interval_name

    def __hash__(self) -> int:
        return hash(self.interval_name)

    def __str__(self) -> str:
        return self.interval_name

    def compare_to(self, other: object) -> int:
        if isinstance(other, SimpleInterval):
            return (self.interval_name > other.interval_name) - (
                self.interval_name < other.interval_name
            )
        return 0
