"""Smoke test for meta/fuzzyActivity/FuzzyActivityMetaSolver (M16).

There is no Java example for FuzzyActivityMetaSolver (the only fuzzy-activity
Java example, ``TestFuzzyActivityNetworkSolver.java``, exercises the
unrelated M9 class ``multi/fuzzyActivity/FuzzyActivityNetworkSolver`` --
different despite the similar name). FuzzyActivityDomain also references the
M20 ``onLineMonitoring`` classes (``Rule``, ``Requirement``,
``MonitoredComponent``, ...), which are not yet ported.

This test builds a minimal scenario using small local stand-in classes that
duck-type the *anticipated* M20 API (attributes ``component``/
``possibilities``/``requirements`` on Rule, ``name``/``states`` on the
component -- following this port's C2 naming convention). These are NOT
ported JUnit assertions and NOT the real M20 classes -- the asserts below
are sanity checks written for this port, confirming the meta-CSP runs end to
end and produces an internally-consistent result. Do not read any of the
numeric assertions as pinned to a Java oracle: there is none for this class.
"""

from __future__ import annotations

from metacsp.meta.fuzzy_activity import FuzzyActivityDomain, FuzzyActivityMetaSolver


class _StubComponent:
    """Duck-typed stand-in for the (not yet ported) M20
    ``onLineMonitoring.MonitoredComponent``: a name plus a list of states."""

    def __init__(self, name: str, states: list[str]) -> None:
        self.name = name
        self.states = states


class _StubRule:
    """Duck-typed stand-in for the (not yet ported) M20
    ``onLineMonitoring.Rule``: a component, a possibility distribution over
    its states, and a (here, empty) list of Requirements -- exercising
    FuzzyActivityDomain without needing the not-yet-ported Sensor/
    Requirement/PhysicalSensor classes."""

    def __init__(self, component: _StubComponent, possibilities: list[float]) -> None:
        self.component = component
        self.possibilities = possibilities
        self.requirements: list[object] = []

    @property
    def head(self) -> str:
        # Mirrors Java Rule.getHead(): the state name whose possibility is 1.0.
        for i, p in enumerate(self.possibilities):
            if p == 1.0:
                return self.component.states[i]
        return ""


class TestFuzzyActivityMetaSolver:
    def test_backtrack_justifies_all_rule_heads(self) -> None:
        """Two independent rules (no sensor requirements) should both be
        unifiable/justifiable by plain backtracking search."""
        domain = FuzzyActivityDomain()
        meta_solver = FuzzyActivityMetaSolver(0)
        meta_solver.add_meta_constraint(domain)

        comp_a = _StubComponent("ContextA", ["on", "off"])
        comp_b = _StubComponent("ContextB", ["hot", "cold"])
        rule_a = _StubRule(comp_a, [1.0, 0.0])
        rule_b = _StubRule(comp_b, [0.0, 1.0])
        domain.add_rule(rule_a)
        domain.add_rule(rule_b)

        # Before solving, both rule heads are unjustified metavariables.
        assert len(domain.get_meta_variables()) == 2

        assert meta_solver.backtrack()

        # A valid solution justifies every rule head.
        assert domain.get_meta_variables() == []
        for head in domain.heads:
            assert head.marking == FuzzyActivityDomain.markings.JUSTIFIED

    def test_branch_and_bound_runs_and_reports_a_consistent_optimum(self) -> None:
        """Branch-and-bound search exhaustively explores the (here, tiny)
        search space and must run to completion without crashing, reporting
        bookkeeping (bounds, optimal constraint network) that is internally
        consistent."""
        domain = FuzzyActivityDomain()
        meta_solver = FuzzyActivityMetaSolver(0)
        meta_solver.add_meta_constraint(domain)

        comp = _StubComponent("Context", ["a", "b", "c"])
        rule = _StubRule(comp, [0.0, 1.0, 0.0])
        domain.add_rule(rule)

        # branch_and_bound() explores exhaustively for the optimum (unlike
        # backtrack(), its boolean return does not mean "a solution was
        # found" once there is at least one metavariable to resolve -- the
        # actual result is read via get_optimal_constraint()/get_lower_bound()).
        meta_solver.branch_and_bound()

        # The reported lower bound must be a valid possibility degree.
        assert 0.0 <= meta_solver.get_lower_bound() <= 1.0
        # An optimal constraint network was recorded.
        assert meta_solver.get_optimal_constraint() is not None
        # get_most_likely_occurred_activities() must run without crashing
        # and mention the rule's head state.
        report = meta_solver.get_most_likely_occurred_activities()
        assert "b" in report

    def test_no_rules_trivially_solved(self) -> None:
        """With no rules there are no metavariables to resolve --
        backtrack() must succeed immediately."""
        domain = FuzzyActivityDomain()
        meta_solver = FuzzyActivityMetaSolver(0)
        meta_solver.add_meta_constraint(domain)
        assert meta_solver.backtrack()
