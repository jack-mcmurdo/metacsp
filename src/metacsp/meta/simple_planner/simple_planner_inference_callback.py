"""Port of meta/simplePlanner/SimplePlannerInferenceCallback.java.

Java's ``SimplePlannerInferenceCallback`` implements the single-method
``org.metacsp.sensing.InferenceCallback`` interface (M19, not yet ported).
Per C4, single-method callback interfaces normally become "accept any
Python callable" -- but this class carries state beyond the callback method
itself (``planner``, ``domain``), so it is ported as a small class instead,
exposing the same ``do_inference(time_now)`` method Java's
``InferenceCallback.doInference(long)`` requires. Instances of this class
are themselves valid callables for that (still-unported) interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.variable_prototype import VariablePrototype
from metacsp.meta.simple_planner.proactive_planning_domain import ProactivePlanningDomain
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.meta.simple_planner.simple_planner import SimplePlanner

__all__ = ["SimplePlannerInferenceCallback"]


class SimplePlannerInferenceCallback:
    """Port of ``SimplePlannerInferenceCallback.java``."""

    def __init__(self, planner: SimplePlanner) -> None:
        self.planner: SimplePlanner | None = planner
        self.logger = get_logger(type(self))
        self.domain: ProactivePlanningDomain | None = None
        for mc in planner.meta_constraints:
            if isinstance(mc, ProactivePlanningDomain):
                self.domain = mc
                break

    def do_inference(self, time_now: int) -> None:
        """Re-run planning at the given time and record any newly inferred activities."""
        if self.planner is not None:
            assert self.domain is not None
            self.domain.reset_context_inference()
            self.domain.update_time_now(time_now)
            self.planner.clear_resolvers()
            self.planner.backtrack()
            for cn in self.planner.get_added_resolvers():
                var: VariablePrototype | None = None
                for v in cn.get_variables():
                    if isinstance(v, VariablePrototype):
                        if len(v.parameters) > 2:
                            if v.parameters[2] == "Inference":
                                var = v
                if var is not None:
                    act = cast(SymbolicVariableActivity, cn.get_substitution(var))
                    self.domain.set_old_inference(cast(str, act.component), act)

    def __call__(self, time_now: int) -> None:
        """Alias for :meth:`do_inference`, so instances satisfy the InferenceCallback protocol."""
        self.do_inference(time_now)
