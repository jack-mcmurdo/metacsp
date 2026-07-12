"""Port of spatial/utility/AssertionalRelation.java."""

from __future__ import annotations

__all__ = ["AssertionalRelation"]


class AssertionalRelation:
    """A named "from -> to" relation between two string-keyed entities, staged
    before being bound to constraint-network variables."""

    def __init__(self, from_: str, to: str) -> None:
        self._from = from_
        self._to = to

    @property
    def from_(self) -> str:
        return self._from

    @from_.setter
    def from_(self, value: str) -> None:
        self._from = value

    @property
    def to(self) -> str:
        return self._to

    @to.setter
    def to(self, value: str) -> None:
        self._to = value
