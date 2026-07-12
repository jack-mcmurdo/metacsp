"""Port of onLineMonitoring/HypothesisNode.java."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from metacsp.multi.fuzzy_activity.fuzzy_activity import FuzzyActivity
    from metacsp.online_monitoring.hypothesis import Hypothesis

__all__ = ["HypothesisNode"]


class HypothesisNode:
    """One node of the (experimental, "Iran") hypothesis-dependency graph
    built by :class:`~metacsp.online_monitoring.domain_description
    .DomainDescription` as ghost-sensor hypotheses are chained across
    inference passes: accumulates the temporal/value/overall consistency
    of ``fa`` plus that of everything it (transitively) depends on."""

    def __init__(
        self,
        fa: FuzzyActivity,
        sigma_tc: float,
        sigma_vc: float,
        sigma_oc: float,
        hyp: Hypothesis,
    ) -> None:
        self.hyp = hyp
        self.fa = fa
        self.sigma_oc = sigma_oc
        self.sigma_tc = sigma_tc
        self.sigma_vc = sigma_vc

    @property
    def fuzzy_activity(self) -> FuzzyActivity:
        return self.fa

    def __str__(self) -> str:
        return (
            f"Id: {self.fa} OC: {self.sigma_oc} TC: {self.sigma_tc} "
            f"VC: {self.sigma_vc} hyp: {self.hyp}"
        )
