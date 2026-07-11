"""Tests for metacsp.framework.multi (M3): a two-level MultiVariable solver
(a MultiConstraintSolver delegating to a plain leaf ConstraintSolver),
exercising variable creation cascades and lifted<->internal constraint
decomposition."""

from __future__ import annotations

import pytest

from metacsp.exceptions import ConstraintNotFound
from metacsp.framework import BinaryConstraint, Constraint, ConstraintSolver, Domain, Variable
from metacsp.framework.multi import MultiBinaryConstraint, MultiConstraintSolver, MultiVariable

# --- leaf-level fixtures (bottom of the two-level hierarchy) ---


class _LeafDomain(Domain):
    def __str__(self) -> str:
        return "leaf-domain"


class _LeafVariable(Variable):
    def __init__(self, cs: ConstraintSolver, id: int) -> None:
        super().__init__(cs, id)
        self._domain: Domain | None = _LeafDomain(self)

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    @property
    def domain(self) -> Domain | None:
        return self._domain

    @domain.setter
    def domain(self, d: Domain) -> None:
        self._domain = d

    def __str__(self) -> str:
        return f"Leaf{self.id}"


class _LeafLink(BinaryConstraint):
    def __init__(self, label: str = "leaf-link") -> None:
        super().__init__()
        self._label = label

    def __str__(self) -> str:
        return self._label

    @property
    def edge_label(self) -> str:
        return self._label

    def clone(self) -> "_LeafLink":
        c = _LeafLink(self._label)
        c.scope = self.scope
        c.auto_removable = self.auto_removable
        return c

    def is_equivalent(self, c: Constraint) -> bool:
        return isinstance(c, _LeafLink) and c.edge_label == self._label


class _LeafSolver(ConstraintSolver):
    def __init__(self) -> None:
        super().__init__([_LeafLink], _LeafVariable)
        self._next_id = 0
        self.add_sub_result = True

    def propagate(self) -> bool:
        return True

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        return self.add_sub_result

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        pass

    def create_variables_sub(self, num: int) -> list[Variable]:
        ret = []
        for _ in range(num):
            ret.append(_LeafVariable(self, self._next_id))
            self._next_id += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        pass

    def register_value_choice_functions(self) -> None:
        pass


# --- multi-level fixtures (top of the two-level hierarchy) ---


class _PairVariable(MultiVariable):
    """A MultiVariable of two leaf variables linked by an internal
    _LeafLink -- stands in for e.g. AllenInterval's two TimePoints plus its
    internal Duration constraint (which Java also marks auto-removable)."""

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        link = _LeafLink("internal")
        link.scope = [variables[0], variables[1]]
        link.auto_removable = True
        return [link]

    def __lt__(self, other: Variable) -> bool:
        return self.id < other.id

    def __str__(self) -> str:
        return f"Pair{self.id}"

    @property
    def domain(self):
        return super().domain

    @domain.setter
    def domain(self, d) -> None:
        pass


class _PairConstraint(MultiBinaryConstraint):
    """Lifted constraint between two PairVariables, decomposed into two
    _LeafLink constraints between their respective internal variables."""

    def create_internal_constraints_from_to(
        self, from_: Variable, to: Variable
    ) -> list[Constraint] | None:
        assert isinstance(from_, MultiVariable) and isinstance(to, MultiVariable)
        links = []
        for i in range(2):
            link = _LeafLink(f"lifted-{i}")
            link.scope = [from_.internal_variables[i], to.internal_variables[i]]
            links.append(link)
        return links

    @property
    def edge_label(self) -> str:
        return "pair-constraint"

    def clone(self) -> "_PairConstraint":
        c = _PairConstraint()
        c.scope = self.scope
        return c

    def is_equivalent(self, c: Constraint) -> bool:
        return isinstance(c, _PairConstraint)


class _PairSolver(MultiConstraintSolver):
    def __init__(self, leaf_solver: _LeafSolver) -> None:
        super().__init__([_PairConstraint], _PairVariable, [leaf_solver], [2])

    def propagate(self) -> bool:
        return True


# --- tests ---


class TestMultiVariableCreation:
    def test_variable_creation_cascades_to_internal_solver(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)

        pairs = top.create_variables(2)
        assert len(pairs) == 2
        assert all(isinstance(p, _PairVariable) for p in pairs)

        for p in pairs:
            assert len(p.internal_variables) == 2
            for iv in p.internal_variables:
                assert iv.parent_variable is p

        assert len(leaf.get_variables()) == 4
        assert set(leaf.get_variables()) == {iv for p in pairs for iv in p.internal_variables}

        # each PairVariable's internal Duration-like constraint landed
        # (unpropagated) in the leaf solver
        assert len(leaf.get_constraints()) == 2
        for p in pairs:
            assert p.internal_constraints[0] in leaf.get_constraints()

    def test_create_variables_with_component_tags_both_levels(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)

        pairs = top.create_variables(1, "comp-a")
        p = pairs[0]
        assert top.get_component(p) == "comp-a"
        for iv in p.internal_variables:
            assert leaf.get_component(iv) == "comp-a"

    def test_remove_variables_cascades(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        pairs = top.create_variables(2)

        removed_internals = list(pairs[0].internal_variables)
        surviving_internals = list(pairs[1].internal_variables)

        top.remove_variable(pairs[0])
        assert pairs[0] not in top.get_variables()
        for iv in removed_internals:
            assert iv not in leaf.get_variables()
        for iv in surviving_internals:
            assert iv in leaf.get_variables()


class TestMultiConstraintDecomposition:
    def test_add_lifted_constraint_decomposes_into_internal_constraints(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        p1, p2 = top.create_variables(2)

        con = _PairConstraint()
        con.scope = [p1, p2]
        n_leaf_before = len(leaf.get_constraints())
        assert top.add_constraint(con) is True
        assert con in top.get_constraints()
        # two new lifted _LeafLink constraints were instantiated in the leaf solver
        assert len(leaf.get_constraints()) == n_leaf_before + 2

    def test_remove_lifted_constraint_removes_internal_constraints(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        p1, p2 = top.create_variables(2)
        con = _PairConstraint()
        con.scope = [p1, p2]
        top.add_constraint(con)
        n_leaf_with_con = len(leaf.get_constraints())

        top.remove_constraint(con)
        assert con not in top.get_constraints()
        assert len(leaf.get_constraints()) == n_leaf_with_con - 2

    def test_remove_constraint_not_instantiated_raises(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        p1, p2 = top.create_variables(2)
        con = _PairConstraint()
        con.scope = [p1, p2]
        with pytest.raises(ConstraintNotFound):
            top.remove_constraint(con)

    def test_add_constraint_rolls_back_on_leaf_failure(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        p1, p2 = top.create_variables(2)
        n_leaf_before = len(leaf.get_constraints())

        leaf.add_sub_result = False
        con = _PairConstraint()
        con.scope = [p1, p2]
        assert top.add_constraint(con) is False
        assert con not in top.get_constraints()
        assert len(leaf.get_constraints()) == n_leaf_before


class TestConstraintSolverHierarchy:
    def test_hierarchy_and_get_constraint_solver(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        assert top.constraint_solvers == [leaf]
        assert MultiConstraintSolver.get_constraint_solver(top, _LeafSolver) is leaf
        assert MultiConstraintSolver.get_constraint_solver(top, _PairSolver) is top
        # exact-type match (mirrors Java's getClass().equals(...)): the
        # abstract base class itself never matches a concrete subclass
        assert MultiConstraintSolver.get_constraint_solver(top, ConstraintSolver) is None

        hierarchy = top.constraint_solver_hierarchy
        assert hierarchy.root is top
        assert hierarchy.children(top) == [leaf]

    def test_options_are_shadowed_from_parent(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        assert top.get_option(MultiConstraintSolver.Options.FORCE_CONSISTENCY) is True
        top.set_options(MultiConstraintSolver.Options.ALLOW_INCONSISTENCIES)
        assert top.get_option(MultiConstraintSolver.Options.ALLOW_INCONSISTENCIES) is True

    def test_variable_hierarchy(self):
        leaf = _LeafSolver()
        top = _PairSolver(leaf)
        (p,) = top.create_variables(1)
        tree = p.variable_hierarchy
        assert tree.root is p
        assert set(tree.children(p)) == set(p.internal_variables)
