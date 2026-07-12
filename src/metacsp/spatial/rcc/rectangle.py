"""Port of spatial/RCC/Rectangle.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.domain import Domain

if TYPE_CHECKING:
    from metacsp.spatial.rcc.region import Region

__all__ = ["Rectangle"]


class Rectangle(Domain):
    """The domain of a Region: a bounding rectangle's width/height and interval names."""

    def __init__(self, v: Region) -> None:
        super().__init__(v)
        self._width = 0
        self._height = 0
        self._interval_name = [f"XInterval{v.id}", f"YInterval{v.id}"]

    @property
    def intervals_name(self) -> str:
        return f"{self._interval_name[0]} {self._interval_name[1]}"

    @property
    def x_interval(self) -> str:
        return self._interval_name[0]

    @property
    def y_interval(self) -> str:
        return self._interval_name[1]

    def compare_to(self, other: object) -> int:
        return 0

    def __str__(self) -> str:
        return f"{self._interval_name[0]} {self._interval_name[1]}"

    @property
    def height(self) -> int:
        return self._height

    @property
    def width(self) -> int:
        return self._width
