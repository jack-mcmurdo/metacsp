"""Tests for metacsp.framework (M2): build networks of DummyVariables and
concrete test Variable/Constraint/ConstraintSolver subclasses, add/remove
constraints, assert graph queries, and that change listeners fire in order."""

from __future__ import annotations

import pytest

from metacsp.exceptions import (
    ConstraintNotFound,
    IllegalValueChoiceFunction,
    IllegalVariableRemoval,
    VariableNotFound,
)
from metacsp.framework import (
    BinaryConstraint,
    Constraint,
    ConstraintNetwork,
    ConstraintSolver,
    Domain,
    DummyConstraint,
    DummyVariable,
    Variable,
    ValueChoiceFunction,
    VariablePrototype,
)

# --- minimal concrete fixtures ---


class _Link(BinaryConstraint):
    def __init__(self, label: str = "link") -> None:
        super().__init__()
        self._label = label

    def __str__(self) -> str:
        return self._label

    @property
    def edge_label(self) -> str:
        return self._label

    def clone(self) -> "_Link":
        c = _Link(self._label)
        c.scope = self.scope
        return c

    def is_equivalent(self, c: Constraint) -> bool:
        return isinstance(c, _Link) and c.edge_label == self._label


class _TriLink(Constraint):
    """A ternary (non-binary) constraint, to exercise the hyperedge path."""

    def __init__(self, label: str = "tri") -> None:
        super().__init__()
        self._label = label

    def __str__(self) -> str:
        return self._label

    @property
    def edge_label(self) -> str:
        return self._label

    def clone(self) -> "_TriLink":
        c = _TriLink(self._label)
        c.scope = self.scope
        return c

    def is_equivalent(self, c: Constraint) -> bool:
        return isinstance(c, _TriLink) and c.edge_label == self._label


class _TestDomain(Domain):
    def __init__(self, variable: Variable, values: list) -> None:
        super().__init__(variable)
        self.values = values

    def __str__(self) -> str:
        return str(self.values)


class _FirstValueVCF(ValueChoiceFunction):
    def get_value(self, dom: _TestDomain):
        return dom.values[0]


class _TestVariable(Variable):
    def __init__(self, cs: ConstraintSolver, id: int, values: list | None = None) -> None:
        super().__init__(cs, id)
        self._domain: Domain | None = _TestDomain(self, values) if values is not None else None

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    @property
    def domain(self) -> Domain | None:
        return self._domain

    @domain.setter
    def domain(self, d: Domain) -> None:
        self._domain = d

    def __str__(self) -> str:
        return f"TV{self.id}"


class _TestSolver(ConstraintSolver):
    def __init__(self) -> None:
        super().__init__([_Link, _TriLink], DummyVariable)
        self.propagate_calls = 0
        self.propagate_result = True
        self.add_sub_result = True
        self._next_id = 0

    def propagate(self) -> bool:
        self.propagate_calls += 1
        return self.propagate_result

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return self.add_sub_result

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(DummyVariable(self, f"v{self._next_id}"))
            self._next_id += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def register_value_choice_functions(self) -> None:
        pass


# --- ConstraintNetwork ---


class TestConstraintNetwork:
    def test_add_remove_variables(self):
        solver = _TestSolver()
        net = solver.constraint_network
        v1 = DummyVariable(solver, "v1")
        v2 = DummyVariable(solver, "v2")
        net.add_variable(v1)
        net.add_variable(v2)
        assert set(net.get_variables()) == {v1, v2}
        assert net.contains_variable(v1)
        assert net.contains_variable(v1.id)
        assert net.get_variable(v1.id) is v1

        net.remove_variable(v1)
        assert not net.contains_variable(v1)
        assert set(net.get_variables()) == {v2}

    def test_binary_constraint_add_remove(self):
        # Uses _TestVariable rather than DummyVariable here because
        # get_neighboring_variables() always returns [] for a DummyVariable
        # query (it is reserved for hyperedge hubs) -- see the faithfully
        # ported guard clause at the top of that method.
        solver = _TestSolver()
        net = solver.constraint_network
        v1, v2 = _TestVariable(solver, 1), _TestVariable(solver, 2)
        net.add_variable(v1)
        net.add_variable(v2)

        c = _Link("c1")
        c.scope = [v1, v2]
        assert net.get_constraint(v1, v2) is None
        net.add_constraint(c)
        assert net.get_constraint(v1, v2) is c
        assert net.contains_constraint(c)
        assert c in net.get_incident_edges(v1)
        assert c in net.get_incident_edges(v2)
        assert net.get_variable_from(c) is v1
        assert net.get_variable_to(c) is v2
        assert net.get_neighboring_variables(v1) == [v2]

        net.remove_constraint(c)
        assert not net.contains_constraint(c)
        assert net.get_incident_edges(v1) == []
        assert net.get_constraint(v1, v2) is None

    def test_hyperedge_constraint(self):
        solver = _TestSolver()
        net = solver.constraint_network
        v1, v2, v3 = (_TestVariable(solver, i) for i in range(3))
        for v in (v1, v2, v3):
            net.add_variable(v)

        tri = _TriLink()
        tri.scope = [v1, v2, v3]
        net.add_constraint(tri)

        assert net.contains_constraint(tri)
        assert tri in net.get_constraints()
        # hub DummyVariable must not leak into get_variables()
        assert set(net.get_variables()) == {v1, v2, v3}
        for v in (v1, v2, v3):
            incident = net.get_incident_edges(v)
            assert len(incident) == 1
            assert isinstance(incident[0], DummyConstraint)
        # neighboring variables traverse through the hub
        assert set(net.get_neighboring_variables(v1)) == {v2, v3}

        net.remove_constraint(tri)
        assert not net.contains_constraint(tri)
        for v in (v1, v2, v3):
            assert net.get_incident_edges(v) == []

    def test_change_listeners_fire_in_order(self):
        solver = _TestSolver()
        net = solver.constraint_network
        events = []
        listener = events.append
        net.add_change_listener(listener)

        v1, v2 = DummyVariable(solver, "v1"), DummyVariable(solver, "v2")
        net.add_variable(v1)
        net.add_variable(v2)
        c = _Link("c")
        c.scope = [v1, v2]
        net.add_constraint(c)
        net.remove_constraint(c)
        net.remove_variable(v2)

        kinds = [e.kind for e in events]
        assert kinds == [
            "variable_added",
            "variable_added",
            "constraint_added",
            "constraint_removed",
            "variable_removed",
        ]
        assert events[0].payload is v1
        assert events[1].payload is v2
        assert events[2].payload is c

        net.remove_change_listener(listener)
        net.remove_variable(v1)
        assert len(events) == 5  # no new event after removal

    def test_clone_join_equals(self):
        solver = _TestSolver()
        net = solver.constraint_network
        v1, v2 = DummyVariable(solver, "v1"), DummyVariable(solver, "v2")
        net.add_variable(v1)
        net.add_variable(v2)
        c = _Link("c")
        c.scope = [v1, v2]
        net.add_constraint(c)

        clone = net.clone()
        assert clone is not net
        assert clone == net
        assert set(clone.get_variables()) == {v1, v2}
        assert clone.contains_constraint(c)

        other = ConstraintNetwork(solver)
        other.join(net)
        assert other == net

    def test_substitutions(self):
        solver = _TestSolver()
        net = solver.constraint_network
        vp = VariablePrototype(solver, "param")
        v = DummyVariable(solver, "v")
        net.add_substitution(vp, v)
        assert net.get_substitution(vp) is v
        assert net.get_substituted(v) is vp
        net.remove_substitution(vp)
        assert net.get_substitution(vp) is None


# --- ConstraintSolver ---


class TestConstraintSolver:
    def test_create_variables_and_component(self):
        solver = _TestSolver()
        v1 = solver.create_variable("comp-a")
        vs = solver.create_variables(2, "comp-a")
        assert solver.get_component(v1) == "comp-a"
        assert set(solver.get_variables("comp-a")) == {v1, *vs}
        assert set(solver.constraint_network.get_variables()) == {v1, *vs}

    def test_add_constraints_success_and_rollback(self):
        solver = _TestSolver()
        solver.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)
        v1, v2 = solver.create_variables(2)  # already triggers one propagate() call
        solver.propagate_calls = 0
        c = _Link("c")
        c.scope = [v1, v2]
        assert solver.add_constraint(c) is True
        assert solver.propagate_calls == 1
        assert c in solver.get_constraints()

        # simulate propagation failure -> constraint must be rolled back
        c2 = _Link("c2")
        c2.scope = [v2, v1]
        solver.propagate_result = False
        assert solver.add_constraint(c2) is False
        assert c2 not in solver.get_constraints()

    def test_add_constraints_sub_failure(self):
        solver = _TestSolver()
        v1, v2 = solver.create_variables(2)
        c = _Link("c")
        c.scope = [v1, v2]
        solver.add_sub_result = False
        assert solver.add_constraint(c) is False
        assert c not in solver.get_constraints()

    def test_remove_constraint_not_found_raises(self):
        solver = _TestSolver()
        v1, v2 = solver.create_variables(2)
        c = _Link("c")
        c.scope = [v1, v2]
        with pytest.raises(ConstraintNotFound):
            solver.remove_constraint(c)

    def test_remove_variable_not_found_raises(self):
        solver = _TestSolver()
        other_solver = _TestSolver()
        stray = other_solver.create_variable()
        with pytest.raises(VariableNotFound):
            solver.remove_variable(stray)

    def test_remove_variable_illegal_removal(self):
        solver = _TestSolver()
        v1, v2 = solver.create_variables(2)
        c = _Link("c")
        c.scope = [v1, v2]
        solver.add_constraint(c)
        with pytest.raises(IllegalVariableRemoval):
            solver.remove_variable(v1)

        c.auto_removable = True
        solver.remove_variable(v1)
        assert v1 not in solver.get_variables()
        assert c not in solver.get_constraints()

    def test_dependent_variable_cascade_removal(self):
        solver_a = _TestSolver()
        solver_b = _TestSolver()
        var_a = solver_a.create_variable()
        var_b = solver_b.create_variable()
        var_a.add_dependent_variables(var_b)

        solver_a.remove_variable(var_a)
        assert var_a not in solver_a.get_variables()
        assert var_b not in solver_b.get_variables()

    def test_options(self):
        solver = _TestSolver()
        assert solver.get_option(ConstraintSolver.Options.MANUAL_PROPAGATE) is True
        solver.set_options(ConstraintSolver.Options.AUTO_PROPAGATE)
        assert solver.get_option(ConstraintSolver.Options.AUTO_PROPAGATE) is True
        assert solver.get_option(ConstraintSolver.Options.MANUAL_PROPAGATE) is False


# --- Domain / ValueChoiceFunction ---


class TestDomain:
    def test_choose_value_default_and_named(self):
        solver = _TestSolver()
        var = _TestVariable(solver, 1000, [3, 1, 2])
        Domain.register_value_choice_function(_TestDomain, _FirstValueVCF(), "first")
        assert var.domain.choose_value("first") == 3
        var.domain.set_default_value_choice_function("first")
        assert var.domain.choose_value() == 3

    def test_choose_value_unknown_raises(self):
        solver = _TestSolver()
        var = _TestVariable(solver, 1001, [9])
        Domain.register_value_choice_function(_TestDomain, _FirstValueVCF(), "first")
        with pytest.raises(IllegalValueChoiceFunction):
            var.domain.choose_value("does-not-exist")


# --- Variable ---


class TestVariable:
    def test_equality_and_hash(self):
        solver = _TestSolver()
        v1 = _TestVariable(solver, 5)
        v1_dup = _TestVariable(solver, 5)
        v2 = _TestVariable(solver, 6)
        assert v1 == v1_dup
        assert v1 != v2
        assert hash(v1) == hash(v1_dup)
        assert {v1, v1_dup, v2} == {v1, v2}

    def test_ordering(self):
        solver = _TestSolver()
        v1 = _TestVariable(solver, 1)
        v2 = _TestVariable(solver, 2)
        assert v1 < v2
        assert sorted([v2, v1]) == [v1, v2]

    def test_dependent_variables_and_root(self):
        solver = _TestSolver()
        parent = _TestVariable(solver, 10)
        child = _TestVariable(solver, 11)
        parent.add_dependent_variables(child)
        assert child.depends_on(parent)
        assert child in parent.dependent_variables
        assert list(parent.recursively_dependent_variables) == [child, parent]
        child.parent_variable = parent
        assert child.root_variable is parent
