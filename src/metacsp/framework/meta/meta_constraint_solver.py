"""Port of framework/meta/MetaConstraintSolver.java.

Backtracking search runs over a :class:`~metacsp.utility.graph.DelegateTree`
(D1, replacing JUNG's ``DelegateForest`` -- only ever a single tree is used
here, so ``DelegateTree`` is a drop-in). The Swing ``SearchTreeFrame`` search
tree viewer (skip list, ``utility/UI``) is not ported; see D10. Java object
serialization used by the (impractical, per the original docstring)
serialization-based backtracking helpers is replaced by ``pickle`` per C10.
"""

from __future__ import annotations

import functools
import pickle
import time
from abc import abstractmethod
from typing import TYPE_CHECKING

from metacsp.exceptions import NoFocusDefinedException
from metacsp.framework.meta.focus_constraint import FocusConstraint
from metacsp.framework.meta.meta_constraint import MetaConstraint
from metacsp.framework.meta.meta_variable import MetaVariable
from metacsp.framework.meta.null_constraint_network import NullConstraintNetwork
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.utility.graph import DelegateTree

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable

__all__ = ["MetaConstraintSolver"]


class MetaConstraintSolver(MultiConstraintSolver):
    """A high-level CSP whose variables/constraints (meta-variables and
    meta-constraints) are defined implicitly over one or more ground CSPs.

    Solving a meta-CSP means finding values (ConstraintNetworks of variables
    and constraints to post to the ground solver(s)) for meta-variables such
    that no MetaConstraint is violated; this class implements backtracking
    search (:meth:`backtrack`) over that search space, plus limited
    branch-and-bound support for constraint optimization (:meth:`branch_and_bound`).
    """

    class TerminalNode(MetaVariable):
        """A terminal (success or failure) leaf of the meta-CSP search tree."""

        def __init__(self, success: bool) -> None:
            super().__init__(None, None)
            self.success = success

        def __str__(self) -> str:
            return "SUCCESS" if self.success else "FAILURE"

    def __init__(
        self,
        constraint_types: list[type],
        animation_time: int,
        *internal_solvers: ConstraintSolver,
    ) -> None:
        super().__init__(constraint_types, MetaVariable, list(internal_solvers), None)
        self.meta_constraints: list[MetaConstraint] = []
        self.g: DelegateTree[MetaVariable, ConstraintNetwork] = DelegateTree()
        self.current_vertex: MetaVariable | None = None
        self._break_search = False
        self.meta_vars_to_meta_cons: dict[ConstraintNetwork, MetaConstraint] = {}
        self.resolvers: dict[ConstraintNetwork, ConstraintNetwork] = {}
        self.resolvers_inverse_mapping: dict[ConstraintNetwork, ConstraintNetwork] = {}
        self.animation_time = animation_time
        self.counter_moves = 0
        self.current_focus: FocusConstraint | None = None
        self._backed_up_cns: list[dict[ConstraintSolver, bytes]] = []
        self._timeout = False

    # --- meta-constraints ---

    def add_meta_constraint(self, meta_constraint: MetaConstraint) -> None:
        """Register a MetaConstraint with this solver, extending its constraint types."""
        self.meta_constraints.append(meta_constraint)
        meta_constraint.set_meta_solver(self)
        found = any(cl is type(meta_constraint) for cl in self.constraint_types)
        if not found:
            self.constraint_types = self.constraint_types + [type(meta_constraint)]

    def get_meta_constraint(self, meta_variable: ConstraintNetwork) -> MetaConstraint | None:
        """The MetaConstraint that resolved the given meta-variable, if any."""
        return self.meta_vars_to_meta_cons.get(meta_variable)

    def get_added_resolvers(self) -> list[ConstraintNetwork]:
        """The meta-values currently posted as resolvers."""
        return list(self.resolvers.values())

    def retract_resolvers(self) -> None:
        """Retract every currently posted resolver."""
        for var, value in list(self.resolvers.items()):
            self.logger.debug("=== ||| === Retracting value: %s", value.get_constraints())
            self.retract_resolver(var, value)
        self.resolvers = {}
        self.resolvers_inverse_mapping = {}
        self.meta_vars_to_meta_cons.clear()

    def clear_resolvers(self) -> None:
        """Forget the currently posted resolvers without retracting their constraints."""
        self.resolvers = {}
        self.meta_vars_to_meta_cons = {}

    def _get_conflict(self) -> MetaVariable | None:
        if not self.meta_constraints:
            return None
        for mc in self.meta_constraints:
            cn = mc.get_meta_variable()
            if cn is not None:
                return MetaVariable(mc, cn)
        return None

    # --- backtracking search hooks (implemented by subclasses) ---

    @abstractmethod
    def pre_backtrack(self) -> None:
        """Extra operations to perform before backtracking over a
        MetaVariable (and before it is even chosen)."""

    @abstractmethod
    def post_backtrack(self, meta_variable: MetaVariable) -> None:
        """Extra operations to perform after branching over a MetaVariable."""

    def backtrack(self) -> bool:
        """Initiate CSP-style backtracking search on the meta-CSP.

        Returns True iff a set of assignments to all MetaVariables which
        satisfies the MetaConstraints was found.
        """
        self.g = DelegateTree()
        self.logger.info("Starting search...")
        conflict = self._get_conflict()
        if conflict is not None:
            self.current_vertex = conflict
            if self._backtrack_helper(conflict):
                self.logger.info("... solution found")
                return True
            return False
        self.logger.info("... no conflicts found")
        return True

    @property
    def time_out(self) -> bool:
        """True iff the last search was interrupted by a timeout."""
        return self._timeout

    def _backtrack_helper(self, meta_variable: MetaVariable) -> bool:
        self.pre_backtrack()
        if self.g.root is None:
            self.g.set_root(self.current_vertex)
        assert self.current_vertex is not None
        most_problematic_network = meta_variable.constraint_network
        assert most_problematic_network is not None
        self.logger.debug("Solving conflict: %s", meta_variable)
        meta_constraint = meta_variable.meta_constraint
        assert meta_constraint is not None
        values = meta_constraint.get_meta_values(meta_variable)
        if values:
            for value in values:
                value.annotation = meta_variable
        if meta_constraint.val_oh is not None and values:
            values = sorted(values, key=functools.cmp_to_key(meta_constraint.val_oh.compare))
        if not values:
            self.g.add_child(
                NullConstraintNetwork(None), self.current_vertex, self.TerminalNode(False)
            )
            self.logger.debug("Failure (1)...")
        else:
            for value in values:
                if self.animation_time != 0:
                    time.sleep(self.animation_time / 1000.0)
                val_string = ""
                if value.get_variables():
                    val_string += f"Vars = {value.get_variables()}"
                if value.get_constraints():
                    val_string += f" Cons = {value.get_constraints()}"
                self.logger.debug("Trying value: %s", val_string)

                if self.add_resolver(most_problematic_network, value):
                    self.resolvers[most_problematic_network] = value
                    self.meta_vars_to_meta_cons[most_problematic_network] = meta_constraint
                    self.resolvers_inverse_mapping[value] = most_problematic_network
                    self.counter_moves += 1

                    self.logger.debug("Success...")

                    meta_constraint.mark_resolved_sub(meta_variable, value)
                    new_conflict = self._get_conflict()

                    if new_conflict is None or self._break_search:
                        self.g.add_child(value, self.current_vertex, self.TerminalNode(True))
                        self._break_search = False
                        return True
                    self.g.add_child(value, self.current_vertex, new_conflict)
                    self.current_vertex = new_conflict
                    if self._backtrack_helper(new_conflict):
                        return True
                    self.logger.debug("Retracting value: %s", value.get_constraints())
                    self.retract_resolver(most_problematic_network, value)
                    del self.resolvers[most_problematic_network]
                    del self.meta_vars_to_meta_cons[most_problematic_network]
                    del self.resolvers_inverse_mapping[value]
                    self.counter_moves -= 1
                else:
                    self.g.add_child(value, self.current_vertex, self.TerminalNode(False))
                    self.logger.debug("Failure... (2)")
        self.logger.debug("Backtracking...")
        self.current_vertex = self.g.parent(self.current_vertex)
        self.post_backtrack(meta_variable)
        return False

    # --- serialization-based backtracking (impractical on real-sized problems,
    # per the Java docstring; kept only for structural parity) ---

    def _backup_cns(self, con_sol: MultiConstraintSolver) -> dict[ConstraintSolver, bytes]:
        current_level: dict[ConstraintSolver, bytes] = {}
        for cs in con_sol.constraint_solvers:
            self.logger.debug("Backing up CN of %s", type(cs).__name__)
            current_level[cs] = pickle.dumps(cs.constraint_network)
            if isinstance(cs, MultiConstraintSolver):
                current_level.update(self._backup_cns(cs))
        return current_level

    def _restore_cns(self) -> None:
        backup = self._backed_up_cns[-1]
        for cs, backed_up_network in backup.items():
            self.logger.debug("Restoring CN of %s", type(cs).__name__)
            cs.constraint_network = pickle.loads(backed_up_network)
        self._backed_up_cns.remove(backup)
        backup.clear()
        self.logger.info(
            "backup queue: %d --> %d", len(self._backed_up_cns) + 1, len(self._backed_up_cns)
        )

    def _backtrack_helper_with_serialization(self, meta_variable: MetaVariable) -> bool:
        self.pre_backtrack()
        if self.g.root is None:
            self.g.set_root(self.current_vertex)
        assert self.current_vertex is not None
        most_problematic_network = meta_variable.constraint_network
        assert most_problematic_network is not None
        meta_constraint = meta_variable.meta_constraint
        assert meta_constraint is not None
        values = meta_constraint.get_meta_values(meta_variable)
        if meta_constraint.val_oh is not None and values:
            values = sorted(values, key=functools.cmp_to_key(meta_constraint.val_oh.compare))
        if not values:
            self.g.add_child(
                NullConstraintNetwork(None), self.current_vertex, self.TerminalNode(False)
            )
            self.logger.debug("Failure (1)...")
        else:
            for value in values:
                if self.animation_time != 0:
                    time.sleep(self.animation_time / 1000.0)
                self.logger.debug("Trying value: %s", value.get_constraints())

                self._backed_up_cns.append(self._backup_cns(self))

                if self.add_resolver(most_problematic_network, value):
                    self.resolvers[most_problematic_network] = value
                    self.meta_vars_to_meta_cons[most_problematic_network] = meta_constraint
                    self.resolvers_inverse_mapping[value] = most_problematic_network
                    self.counter_moves += 1

                    self.logger.debug("Success...")

                    meta_constraint.mark_resolved_sub(meta_variable, value)
                    new_conflict = self._get_conflict()

                    if new_conflict is None or self._break_search:
                        self.g.add_child(value, self.current_vertex, self.TerminalNode(True))
                        self._break_search = False
                        return True
                    self.g.add_child(value, self.current_vertex, new_conflict)
                    self.current_vertex = new_conflict
                    # Mirrors the Java source, which recurses into the plain
                    # (non-serialization) helper here -- not a typo of ours.
                    if self._backtrack_helper(new_conflict):
                        return True
                    self.logger.debug("Retracting value: %s", value.get_constraints())

                    self._restore_cns()
                    self.retract_resolver_sub(most_problematic_network, value)
                    del self.resolvers[most_problematic_network]
                    del self.meta_vars_to_meta_cons[most_problematic_network]
                    del self.resolvers_inverse_mapping[value]
                    self.counter_moves -= 1
                else:
                    self.g.add_child(value, self.current_vertex, self.TerminalNode(False))
                    self.logger.debug("Failure... (2)")
        self.logger.debug("Backtracking...")
        self.current_vertex = self.g.parent(self.current_vertex)
        self.post_backtrack(meta_variable)
        return False

    # --- resolvers ---

    def add_resolver(
        self, meta_var_constraint_network: ConstraintNetwork, resolver_network: ConstraintNetwork
    ) -> bool:
        """Post a meta-value's constraints to the relevant ground solvers.

        Returns True iff the meta-value's constraints were consistent with the ground CSP
        (in which case they are now posted); rolls back and returns False otherwise.
        """
        if not self.add_resolver_sub(meta_var_constraint_network, resolver_network):
            return False
        solvers_to_constraints: dict[ConstraintSolver, list[Constraint]] = {}
        for c in resolver_network.get_constraints():
            solvers_to_constraints.setdefault(c.scope[0].constraint_solver, []).append(c)
        added_constraints: list[list[Constraint]] = []
        for cs, cons in solvers_to_constraints.items():
            if cs.add_constraints(*cons):
                added_constraints.append(cons)
            else:
                for to_del in added_constraints:
                    to_del[0].scope[0].constraint_solver.remove_constraints(to_del)
                self.retract_resolver_sub(meta_var_constraint_network, resolver_network)
                return False
        return True

    def retract_resolver(self, meta_var: ConstraintNetwork, res: ConstraintNetwork) -> None:
        """Retract a previously posted meta-value's constraints from the ground solvers."""
        self.logger.debug("Retracting resolver:")
        self.logger.debug("  MetaVariable: %s", meta_var)
        self.logger.debug("  MetaValue: %s", res)

        solvers_to_constraints: dict[ConstraintSolver, list[Constraint]] = {}
        for c in res.get_constraints():
            solvers_to_constraints.setdefault(c.scope[0].constraint_solver, []).append(c)
        for cs, cons in solvers_to_constraints.items():
            cs.remove_constraints(cons)

        self.retract_resolver_sub(meta_var, res)
        self.logger.debug("Done retracting resolver.")

    def propagate(self) -> bool:
        """No-op: propagation for meta-CSPs happens via :meth:`backtrack`, not this hook."""
        return False

    @abstractmethod
    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        """Extra operations to perform after retracting a meta-value (e.g.
        when backtracking)."""

    @abstractmethod
    def add_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> bool:
        """Extra operations to perform before adding a meta-value (e.g. when
        branching). Return True iff the meta-value is consistent with the
        ground-CSP (if False, the ground-CSP is left unchanged)."""

    def get_ground_variables(self) -> dict[ConstraintSolver, list[Variable]]:
        """All Variables of each ground solver, keyed by that solver."""
        return {cs: cs.get_variables() for cs in self.constraint_solvers}

    def draw(self) -> None:
        """Draw the search space of the meta-CSP.

        The Java Swing ``SearchTreeFrame`` viewer is not ported (skip list);
        a browser-based search-tree view is future work (D10).
        """
        raise NotImplementedError("the Swing search-tree viewer is not ported; see D10")

    def break_search(self) -> None:
        """Interrupt the current meta-CSP search."""
        self._break_search = True

    # --- branch and bound (limited support for constraint optimization) ---

    def branch_and_bound(self) -> bool:
        """Backtracking search with branch-and-bound pruning for constraint optimization.

        Returns True iff a set of assignments satisfying the MetaConstraints was found.
        """
        self.g = DelegateTree()
        self.logger.info("Starting search...")
        con = self._get_conflict()
        if con is not None:
            self.current_vertex = con
            if self._branch_and_bound_helper(con):
                self.logger.info("... solution found")
                return True
            return False
        self.logger.info("... no conflicts found")
        return True

    def _branch_and_bound_helper(self, meta_variable: MetaVariable | None) -> bool:
        if meta_variable is None:
            return False

        self.pre_backtrack()

        if self.g.root is None:
            self.g.set_root(self.current_vertex)
        cn = meta_variable.constraint_network
        assert cn is not None

        self.logger.debug("Solving conflict: %s", meta_variable)
        meta_constraint = meta_variable.meta_constraint
        assert meta_constraint is not None
        values = meta_constraint.get_meta_values(meta_variable)

        if meta_constraint.val_oh is not None:
            values = sorted(values, key=functools.cmp_to_key(meta_constraint.val_oh.compare))

        if not values:
            self.g.add_child(
                NullConstraintNetwork(None), self.current_vertex, self.TerminalNode(False)
            )
            self.logger.debug("Failure... (1)")
        else:
            for value in values:
                if self.animation_time != 0:
                    time.sleep(self.animation_time / 1000.0)
                self.logger.debug("Trying value: %s", value.get_constraints())

                if self.has_conflict_clause(value):
                    continue

                self.add_resolver(cn, value)
                self.set_upper_bound()
                if self.get_upper_bound() <= self.get_lower_bound():
                    self.retract_resolver(cn, value)
                    continue

                self.logger.debug("Success...")

                meta_constraint.mark_resolved_sub(meta_variable, value)
                new_con = self._get_conflict()
                if new_con is not None:
                    self.g.add_child(value, self.current_vertex, new_con)
                    self.current_vertex = new_con
                if new_con is None:
                    self.set_lower_bound()
                if self._branch_and_bound_helper(new_con):
                    return True
                self.logger.debug("Retracting value: %s", value.get_constraints())
                self.retract_resolver(cn, value)
                self.logger.debug("Failure... (2)")
        self.reset_false_clause()
        self.logger.debug("Backtracking...")
        self.current_vertex = self.g.parent(self.current_vertex)
        self.post_backtrack(meta_variable)
        return False

    @abstractmethod
    def get_upper_bound(self) -> float:
        """Current upper bound on the objective, used by :meth:`branch_and_bound`."""
        ...

    @abstractmethod
    def set_upper_bound(self) -> None:
        """Recompute the upper bound after posting a new resolver."""
        ...

    @abstractmethod
    def get_lower_bound(self) -> float:
        """Current lower bound on the objective, used by :meth:`branch_and_bound`."""
        ...

    @abstractmethod
    def set_lower_bound(self) -> None:
        """Recompute the lower bound once a complete solution is found."""
        ...

    @abstractmethod
    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        """True iff the given meta-value is already known (via a conflict clause) to fail."""
        ...

    @abstractmethod
    def reset_false_clause(self) -> None:
        """Clear any conflict clauses recorded during the current branch-and-bound node."""
        ...

    def failure_pruning(self, failure_time: int) -> None:
        """Reset search state (as :meth:`MultiConstraintSolver.failure_pruning`),
        plus the meta-CSP search tree and resolver bookkeeping."""
        super().failure_pruning(failure_time)
        self.counter_moves = 0
        self.g = DelegateTree()
        self.resolvers.clear()
        self.meta_vars_to_meta_cons.clear()

    # --- focus ---

    @property
    def current_focus_constraint(self) -> FocusConstraint | None:
        """The FocusConstraint currently restricting search, if any."""
        return self.current_focus

    @current_focus_constraint.setter
    def current_focus_constraint(self, focus: FocusConstraint) -> None:
        """Set the FocusConstraint currently restricting search."""
        self.current_focus = focus

    @property
    def focused(self) -> list[Variable] | None:
        """The Variables in scope of the current focus, if any."""
        if self.current_focus is not None:
            return self.current_focus.scope
        return None

    def set_focus(self, *vars: Variable) -> None:
        """Restrict search to the given Variables, replacing any existing focus."""
        self.current_focus = FocusConstraint()
        self.current_focus.scope = list(vars)

    def is_focused(self, var: Variable) -> bool:
        """True iff the given Variable is in the current focus."""
        if self.current_focus is None:
            return False
        focused = self.focused
        assert focused is not None
        return any(v == var for v in focused)

    def focus(self, *vars: Variable) -> None:
        """Add the given Variables to the current focus, creating one if none exists."""
        if self.current_focus is None:
            self.current_focus = FocusConstraint()
        scope_vars = list(self.current_focus.scope)
        scope_vars.extend(vars)
        self.current_focus.scope = scope_vars

    def remove_from_current_focus(self, *vars: Variable) -> None:
        """Remove the given Variables from the current focus."""
        if self.current_focus is None:
            raise NoFocusDefinedException(*vars)
        new_scope = [v_old for v_old in self.current_focus.scope if v_old not in vars]
        self.current_focus.scope = new_scope
