"""Port of multi/activity/ActivityComparator.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.multi.activity.activity import Activity

__all__ = ["ActivityComparator"]


class ActivityComparator:
    """Orders Activities by their temporal variable's earliest start time
    (EST) or earliest end time (EET)."""

    def __init__(self, est: bool) -> None:
        self.est = est

    def compare(self, o1: Activity, o2: Activity) -> int:
        if self.est:
            return o1.temporal_variable.est - o2.temporal_variable.est
        return o1.temporal_variable.eet - o2.temporal_variable.eet
