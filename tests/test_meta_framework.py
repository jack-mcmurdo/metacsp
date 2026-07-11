"""Tests for metacsp.framework.meta (M4): a minimal meta-CSP built on a
dummy ground solver, whose MetaConstraint fabricates a conflict between two
ground variables with two candidate resolvers (one rejected at ground level,
one accepted) -- exercises MetaConstraintSolver's backtracking search,
MultiMetaConstraint's sub-constraint selection, and FocusConstraint."""

from __future__ import annotations

import pytest

from metacsp.exceptions import NoFocusDefinedException
from metacsp.framework import (
    BinaryConstraint,
    Constraint,
    ConstraintNetwork,
    ConstraintOrderingH,
    ConstraintSolver,
    Domain,
    Variable,
)
from metacsp.framework.meta import (
    FocusConstraint,
    MetaConstraint,
    MetaConstraintSolver,
    MultiMetaConstraint,
    NullConstraintNetwork,
)

# --- ground-level fixtures ---


class _ResourceDomain(Domain):
    def __str__(self) -> str:
        return "resource-domain"


class _ResourceVariable(Variable):
    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._domain: Domain | None = _ResourceDomain(self)

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    @property
    def domain(self) -> Domain | None:
        return self._domain

    @domain.setter
    def domain(self, d: Domain) -> None:
        self._domain = d

    def __str__(self) -> str:
        return f"Res{self.id}"


class _PrecedenceConstraint(BinaryConstraint):
    """A ground constraint that a dummy ground solver may reject, standing in
    for e.g. a temporal ordering constraint a real scheduler would post."""

    def __init__(self, reject: bool = False) -> None:
        super().__init__()
        self.reject = reject

    @property
    def edge_label(self) -> str:
        return "before(reject)" if self.reject else "before"

    def clone(self) -> "_PrecedenceConstraint":
        c = _PrecedenceConstraint(self.reject)
        c.scope = self.scope
        return c

    def is_equivalent(self, c: Constraint) -> bool:
        return isinstance(c, _PrecedenceConstraint) and c.scope == self.scope


class _ResourceSolver(ConstraintSolver):
    def __init__(self) -> None:
        super().__init__([_PrecedenceConstraint], _ResourceVariable)
        self._next_id = 0

    def propagate(self) -> bool:
        return True

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return not any(con.reject for con in c)  # type: ignore[attr-defined]

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(_ResourceVariable(self, self._next_id))
            self._next_id += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def register_value_choice_functions(self) -> None:
        pass


# --- meta-level fixtures ---


class _ConflictMetaConstraint(MetaConstraint):
    """Fabricates a conflict between two ground Variables while
    ``remaining_conflicts`` is positive, with two candidate resolvers: one
    that the ground solver rejects (``reject=True``), one it accepts."""

    def __init__(
        self,
        ground_solver: ConstraintSolver,
        a: Variable,
        b: Variable,
        remaining_conflicts: int = 1,
    ) -> None:
        super().__init__(None, None)
        self.ground_solver = ground_solver
        self.a = a
        self.b = b
        self.remaining_conflicts = remaining_conflicts

    def get_meta_variables(self) -> list[ConstraintNetwork]:
        if self.remaining_conflicts <= 0:
            return []
        cn = ConstraintNetwork(None)
        cn.add_variable(self.a)
        cn.add_variable(self.b)
        return [cn]

    def get_meta_values(self, meta_variable) -> list[ConstraintNetwork]:
        bad = ConstraintNetwork(None)
        c_bad = _PrecedenceConstraint(reject=True)
        c_bad.scope = [self.a, self.b]
        bad.add_constraint(c_bad)

        good = ConstraintNetwork(None)
        c_good = _PrecedenceConstraint(reject=False)
        c_good.scope = [self.b, self.a]
        good.add_constraint(c_good)

        return [bad, good]

    def mark_resolved_sub(self, meta_variable, meta_value) -> None:
        self.remaining_conflicts -= 1

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def get_ground_solver(self) -> ConstraintSolver:
        return self.ground_solver

    def __str__(self) -> str:
        return f"ConflictMC(remaining={self.remaining_conflicts})"

    @property
    def edge_label(self) -> str:
        return "conflict"

    def clone(self) -> "_ConflictMetaConstraint":
        return _ConflictMetaConstraint(self.ground_solver, self.a, self.b, self.remaining_conflicts)

    def is_equivalent(self, c: Constraint) -> bool:
        return isinstance(c, _ConflictMetaConstraint) and c.a == self.a and c.b == self.b


class _AlwaysRejectMetaConstraint(_ConflictMetaConstraint):
    """Like _ConflictMetaConstraint, but both candidate resolvers are rejected."""

    def get_meta_values(self, meta_variable) -> list[ConstraintNetwork]:
        bad1 = ConstraintNetwork(None)
        c1 = _PrecedenceConstraint(reject=True)
        c1.scope = [self.a, self.b]
        bad1.add_constraint(c1)

        bad2 = ConstraintNetwork(None)
        c2 = _PrecedenceConstraint(reject=True)
        c2.scope = [self.b, self.a]
        bad2.add_constraint(c2)

        return [bad1, bad2]


class _TestMetaSolver(MetaConstraintSolver):
    def __init__(self, ground_solver: ConstraintSolver) -> None:
        super().__init__([_ConflictMetaConstraint], 0, ground_solver)
        self.pre_backtrack_calls = 0
        self.post_backtrack_calls = 0

    def pre_backtrack(self) -> None:
        self.pre_backtrack_calls += 1

    def post_backtrack(self, meta_variable) -> None:
        self.post_backtrack_calls += 1

    def add_resolver_sub(self, meta_variable, meta_value) -> bool:
        return True

    def retract_resolver_sub(self, meta_variable, meta_value) -> None:
        pass

    def get_upper_bound(self) -> float:
        return 0.0

    def set_upper_bound(self) -> None:
        pass

    def get_lower_bound(self) -> float:
        return 0.0

    def set_lower_bound(self) -> None:
        pass

    def has_conflict_clause(self, meta_value) -> bool:
        return False

    def reset_false_clause(self) -> None:
        pass


class _PreferHigherRemaining(ConstraintOrderingH):
    def collect_data(self, all_meta_constraints) -> None:
        pass

    def compare(self, c1: _ConflictMetaConstraint, c2: _ConflictMetaConstraint) -> int:
        return c2.remaining_conflicts - c1.remaining_conflicts


class _TestMultiMetaConstraint(MultiMetaConstraint):
    def get_meta_variables(self) -> list[ConstraintNetwork]:
        return []

    def get_meta_values(self, meta_variable) -> list[ConstraintNetwork]:
        return []

    def mark_resolved_sub(self, meta_variable, meta_value) -> None:
        pass

    def draw(self, network: ConstraintNetwork) -> None:
        pass

    def get_ground_solver(self) -> ConstraintSolver | None:
        return None

    def __str__(self) -> str:
        return "TestMultiMetaConstraint"

    @property
    def edge_label(self) -> str:
        return "multi"

    def clone(self) -> "_TestMultiMetaConstraint":
        return _TestMultiMetaConstraint(
            self.var_oh, self.val_oh, self.my_constraint_ordering_h, *self.my_meta_cons
        )

    def is_equivalent(self, c: Constraint) -> bool:
        return isinstance(c, _TestMultiMetaConstraint)


# --- tests ---


class TestMetaConstraintSolverBacktracking:
    def test_backtrack_retries_after_rejected_value_and_succeeds(self):
        ground = _ResourceSolver()
        a, b = ground.create_variables(2)
        meta_constraint = _ConflictMetaConstraint(ground, a, b, remaining_conflicts=2)
        solver = _TestMetaSolver(ground)
        solver.add_meta_constraint(meta_constraint)

        assert solver.backtrack() is True
        assert solver.counter_moves == 2
        assert len(solver.get_added_resolvers()) == 2
        assert len(ground.get_constraints()) == 2
        assert all(not c.reject for c in ground.get_constraints())  # type: ignore[attr-defined]
        # both conflicts were resolved on the first (accepted) try -- no
        # branch was ever abandoned, so postBacktrack never fired
        assert solver.pre_backtrack_calls == 2
        assert solver.post_backtrack_calls == 0

    def test_backtrack_returns_false_and_rolls_back_when_all_values_rejected(self):
        ground = _ResourceSolver()
        a, b = ground.create_variables(2)
        meta_constraint = _AlwaysRejectMetaConstraint(ground, a, b, remaining_conflicts=1)
        solver = _TestMetaSolver(ground)
        solver.add_meta_constraint(meta_constraint)

        assert solver.backtrack() is False
        assert solver.resolvers == {}
        assert len(ground.get_constraints()) == 0
        assert solver.pre_backtrack_calls == 1
        assert solver.post_backtrack_calls == 1

    def test_backtrack_with_no_conflicts_succeeds_trivially(self):
        ground = _ResourceSolver()
        a, b = ground.create_variables(2)
        meta_constraint = _ConflictMetaConstraint(ground, a, b, remaining_conflicts=0)
        solver = _TestMetaSolver(ground)
        solver.add_meta_constraint(meta_constraint)

        assert solver.backtrack() is True
        assert solver.counter_moves == 0
        assert solver.get_added_resolvers() == []


class TestMultiMetaConstraint:
    def test_picks_meta_variable_from_higher_priority_sub_constraint(self):
        ground = _ResourceSolver()
        a, b, c, d = ground.create_variables(4)
        mc_low = _ConflictMetaConstraint(ground, a, b, remaining_conflicts=1)
        mc_high = _ConflictMetaConstraint(ground, c, d, remaining_conflicts=5)

        multi = _TestMultiMetaConstraint(None, None, _PreferHigherRemaining(), mc_low, mc_high)
        mv = multi.get_meta_variable()

        assert mv is not None
        assert set(mv.get_variables()) == {c, d}


class TestFocusConstraint:
    def test_is_equivalent_ignores_order(self):
        ground = _ResourceSolver()
        a, b = ground.create_variables(2)
        f1 = FocusConstraint()
        f1.scope = [a, b]
        f2 = FocusConstraint()
        f2.scope = [b, a]
        assert f1.is_equivalent(f2)

    def test_clone_copies_scope(self):
        ground = _ResourceSolver()
        a, b = ground.create_variables(2)
        f = FocusConstraint()
        f.scope = [a, b]
        clone = f.clone()
        assert clone.scope == [a, b]
        assert clone is not f


class TestMetaConstraintSolverFocus:
    def test_set_focus_and_is_focused(self):
        ground = _ResourceSolver()
        a, b, c = ground.create_variables(3)
        solver = _TestMetaSolver(ground)

        solver.set_focus(a, b)
        assert solver.is_focused(a)
        assert solver.is_focused(b)
        assert not solver.is_focused(c)
        assert solver.current_focus_constraint is not None

        solver.focus(c)
        assert solver.is_focused(c)

        solver.remove_from_current_focus(a)
        assert not solver.is_focused(a)
        assert solver.is_focused(b)

    def test_remove_from_current_focus_without_focus_raises(self):
        ground = _ResourceSolver()
        (a,) = ground.create_variables(1)
        solver = _TestMetaSolver(ground)
        with pytest.raises(NoFocusDefinedException):
            solver.remove_from_current_focus(a)


class TestNullConstraintNetwork:
    def test_str(self):
        assert str(NullConstraintNetwork(None)) == "conflicting"
