"""Port of multi/fuzzyActivity/SimpleTimeline.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.time.bounds import INF, Bounds

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["SimpleTimeline"]


class SimpleTimeline:
    """A simple mapping of Variables to their [start,end] Bounds on a
    named component."""

    def __init__(self, component: str) -> None:
        self.component = component
        self.mapping: dict[Bounds, Variable] = {}

    def add_variable(self, v: Variable) -> None:
        i = Bounds(-INF, INF)
        self.mapping[i] = v

    def __str__(self) -> str:
        ret = f"[{self.component}]"
        for i, v in self.mapping.items():
            ret += f" {i} {v}"
        return ret

    def get_mapping(self) -> dict[Bounds, Variable]:
        return self.mapping

    def get_start(self, v: Variable) -> int:
        for i, mapped in self.mapping.items():
            if mapped == v:
                return i.min
        return -1

    def get_end(self, v: Variable) -> int:
        for i, mapped in self.mapping.items():
            if mapped == v:
                return i.max
        return -1

    def set_start(self, v: Variable, t: int) -> None:
        to_remove: Bounds | None = None
        to_replace: Bounds | None = None
        for i, mapped in self.mapping.items():
            if mapped == v:
                to_remove = i
                to_replace = Bounds(t, i.max)
        if to_remove is not None:
            del self.mapping[to_remove]
            assert to_replace is not None
            self.mapping[to_replace] = v
        else:
            self.mapping[Bounds(t, INF)] = v

    def set_end(self, v: Variable, t: int) -> None:
        to_remove: Bounds | None = None
        to_replace: Bounds | None = None
        for i, mapped in self.mapping.items():
            if mapped == v:
                to_remove = i
                to_replace = Bounds(i.min, t)
        if to_remove is not None:
            del self.mapping[to_remove]
            assert to_replace is not None
            self.mapping[to_replace] = v
        else:
            self.mapping[Bounds(-INF, t)] = v
