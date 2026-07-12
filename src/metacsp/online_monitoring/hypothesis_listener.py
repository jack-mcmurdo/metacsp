"""Port of onLineMonitoring/HypothesisListener.java.

A single-method callback interface (C4): any Python callable of signature
``(list[Hypothesis]) -> None`` is accepted wherever a ``HypothesisListener``
is expected, e.g. by :meth:`~metacsp.online_monitoring.domain_description
.DomainDescription.register_hypothesis_listener`. Java's single method is
``processHypotheses(Hypothesis[] hypotheses)``.
"""

from __future__ import annotations

from typing import Callable, List

from metacsp.online_monitoring.hypothesis import Hypothesis

__all__ = ["HypothesisListener"]

HypothesisListener = Callable[[List[Hypothesis]], None]
