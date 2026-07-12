"""Port of framework/ConstraintNetwork.java.

Rendering (``draw()``, Swing JFrame) is not ported -- see skip list; M21
provides JSON serialization instead. Java's reflective ``clone()``
(``getConstructor(ConstraintSolver.class).newInstance(...)``) is replaced
per C5 by calling ``type(self)(self.solver)`` directly, since Python classes
are first-class objects.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from metacsp.framework.binary_constraint import BinaryConstraint
from metacsp.framework.constraint_network_change_event import ConstraintNetworkChangeEvent
from metacsp.framework.constraint_network_marking import ConstraintNetworkMarking
from metacsp.framework.dummy_constraint import DummyConstraint
from metacsp.framework.dummy_variable import DummyVariable
from metacsp.utility.graph import DirectedSparseMultigraph
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable
    from metacsp.framework.variable_prototype import VariablePrototype

__all__ = ["ConstraintNetwork", "mask_constraints", "unmask_constraints"]

ChangeListener = Callable[["ConstraintNetworkChangeEvent"], None]


class ConstraintNetwork:
    """Maintains a network of Variables and Constraints as a graph.

    Used by all ConstraintSolvers; provides add/remove for Variables and
    Constraints and queries over the network (incident edges, etc.).

    Change notifications (D2): register a callable of signature
    ``(ConstraintNetworkChangeEvent) -> None`` with :meth:`add_change_listener`;
    it is invoked once per added/removed Variable or Constraint.
    """

    _next_network_id: ClassVar[int] = 0

    def __init__(self, sol: ConstraintSolver | None) -> None:
        self.solver = sol
        self._graph: DirectedSparseMultigraph[Variable, Constraint] = DirectedSparseMultigraph()
        self._variables: dict[int, Variable] = {}
        self._substitutions: dict[VariablePrototype, Variable] = {}
        self._substituted: dict[Variable, VariablePrototype] = {}
        self._hyper_edges: dict[Constraint, DummyVariable] = {}
        self._listeners: list[ChangeListener] = []
        self._weight: float = -1.0
        self.annotation: Any = "NONE"
        self.specialized_annotation: Any = None
        self.marking: ConstraintNetworkMarking = ConstraintNetworkMarking()
        self.logger = get_logger(type(self))

        self.id = ConstraintNetwork._next_network_id
        ConstraintNetwork._next_network_id += 1

    @property
    def graph(self) -> DirectedSparseMultigraph[Variable, Constraint]:
        """The underlying directed multigraph backing this network."""
        return self._graph

    # --- change listeners (D2) ---

    def add_change_listener(self, listener: ChangeListener) -> None:
        """Register a callable invoked on every added/removed Variable or Constraint."""
        self._listeners.append(listener)

    def remove_change_listener(self, listener: ChangeListener) -> None:
        """Unregister a change listener previously added with :meth:`add_change_listener`."""
        self._listeners.remove(listener)

    def _dispatch(self, kind: Any, payload: Variable | Constraint) -> None:
        if not self._listeners:
            return
        event = ConstraintNetworkChangeEvent(kind, payload)
        for listener in self._listeners:
            listener(event)

    # --- VariablePrototype substitutions ---

    def add_substitution(self, vp: VariablePrototype, v: Variable) -> None:
        """Track the correspondence between a VariablePrototype and the
        concrete Variable created for it (useful when ConstraintNetworks are
        used as meta-values in MetaConstraintSolvers)."""
        self._substitutions[vp] = v
        self._substituted[v] = vp
        self.logger.debug("Added substitution %s <-- %s", vp, v)

    def add_substitutions(self, vp2v: dict[VariablePrototype, Variable]) -> None:
        """Call :meth:`add_substitution` for each VariablePrototype/Variable pair."""
        for vp, v in vp2v.items():
            self.add_substitution(vp, v)

    def get_substitution(self, vp: VariablePrototype) -> Variable | None:
        """The concrete Variable substituted for the given VariablePrototype, if any."""
        return self._substitutions.get(vp)

    def get_substituted(self, v: Variable) -> VariablePrototype | None:
        """The VariablePrototype that the given Variable was substituted for, if any."""
        return self._substituted.get(v)

    def remove_substitution(self, vp: VariablePrototype) -> None:
        """Remove the substitution recorded for the given VariablePrototype, if any."""
        v = self._substitutions.pop(vp, None)
        if v is not None:
            self._substituted.pop(v, None)

    @property
    def substitutions(self) -> dict[VariablePrototype, Variable]:
        """Mapping from VariablePrototype to the concrete Variable substituted for it."""
        return self._substitutions

    @property
    def inverse_substitutions(self) -> dict[Variable, VariablePrototype]:
        """Mapping from concrete Variable back to the VariablePrototype it was substituted for."""
        return self._substituted

    # --- constraint lookups ---

    def get_constraint(self, from_: Variable, to: Variable) -> Constraint | None:
        """A Constraint between two Variables (if it exists); no guarantee
        about which one is returned if several exist."""
        edges = self._graph.find_edge_set(from_, to)
        return edges[0] if edges else None

    def get_constraints_between(self, from_: Variable, to: Variable) -> list[Constraint]:
        """All Constraints directly connecting the two given Variables."""
        return self._graph.find_edge_set(from_, to)

    # --- variables ---

    def add_variable(self, v: Variable) -> None:
        """Add a Variable to the network and notify change listeners."""
        self._graph.add_vertex(v)
        self._variables[v.id] = v
        self.logger.debug("Added variable %s", v)
        self._dispatch("variable_added", v)

    def remove_variable(self, v: Variable) -> None:
        """Remove a Variable from the network and notify change listeners."""
        self._graph.remove_vertex(v)
        self._variables.pop(v.id, None)
        self.logger.debug("Removed variable %s", v)
        self._dispatch("variable_removed", v)

    # --- constraints ---

    def add_constraints(self, *cons: Constraint) -> None:
        """Call :meth:`add_constraint` for each given Constraint."""
        for c in cons:
            self.add_constraint(c)

    def add_constraint(self, c: Constraint) -> None:
        """Add a Constraint to the network.

        Binary constraints become a single graph edge; other (n-ary)
        constraints become a DummyVariable hub connected to each Variable in
        the scope via a DummyConstraint edge each ("hyperedge").
        """
        if isinstance(c, BinaryConstraint):
            self._graph.add_edge(c, c.scope[0], c.scope[1])
            self.logger.debug("Added binary constraint %s", c)
        else:
            dv = DummyVariable(self.solver, c.edge_label)
            self._hyper_edges[c] = dv
            self._graph.add_vertex(dv)
            for var in c.scope:
                dm = DummyConstraint("")
                dm.scope = [dv, var]
                self._graph.add_edge(dm, dv, var)
            self.logger.debug("Added constraint %s", c)
        self._dispatch("constraint_added", c)

    def remove_constraint(self, c: Constraint) -> None:
        """Remove a Constraint from the network and notify change listeners."""
        if isinstance(c, BinaryConstraint):
            self._graph.remove_edge(c)
            self.logger.debug("Removed binary constraint %s", c)
            self._dispatch("constraint_removed", c)
        elif not isinstance(c, DummyConstraint):
            dv = self._hyper_edges.get(c)
            if dv is not None:
                for incident in list(self._graph.incident_edges(dv)):
                    self._graph.remove_edge(incident)
                self._graph.remove_vertex(dv)
                self._hyper_edges.pop(c, None)
                self.logger.debug("Removed constraint %s", c)
                self._dispatch("constraint_removed", c)

    def get_variable_from(self, c: Constraint) -> Variable:
        """The source Variable of a binary Constraint's graph edge."""
        return self._graph.source(c)

    def get_variable_to(self, c: Constraint) -> Variable:
        """The destination Variable of a binary Constraint's graph edge."""
        return self._graph.dest(c)

    def get_variable(self, id: int) -> Variable | None:
        """The Variable with the given id, if it is in this network."""
        return self._variables.get(id)

    def check_domains_instantiated(self) -> Variable | None:
        """None if all domains are instantiated; the first Variable found
        with an uninstantiated domain otherwise."""
        for v in self.get_variables():
            if v.domain is None:
                return v
        return None

    def get_incident_edges(self, v: Variable) -> list[Constraint]:
        """All Constraints (incoming and outgoing) touching the given Variable."""
        result: dict[Constraint, None] = {}
        for e in self._graph.in_edges(v):
            result[e] = None
        for e in self._graph.out_edges(v):
            result[e] = None
        return list(result)

    def get_incident_edges_including_dependent_variables(self, v: Variable) -> list[Constraint]:
        """Like :meth:`get_incident_edges`, extended recursively over ``v``'s dependent variables."""
        result: dict[Constraint, None] = {}
        for con in self.get_incident_edges(v):
            result[con] = None
        for var in v.dependent_variables:
            for (
                con
            ) in var.constraint_solver.get_constraint_network().get_incident_edges_including_dependent_variables(
                var
            ):
                result[con] = None
        return list(result)

    def get_ingoing_edges(self, v: Variable) -> list[Constraint]:
        """Constraints for which the given Variable is the destination."""
        return list(dict.fromkeys(self._graph.in_edges(v)))

    def get_outgoing_edges(self, v: Variable) -> list[Constraint]:
        """Constraints for which the given Variable is the source."""
        return list(dict.fromkeys(self._graph.out_edges(v)))

    def get_variables(
        self, component: str | None = None, *markings_to_exclude: Any
    ) -> list[Variable]:
        """All Variables in the network, or all with a given component
        (unifies Java's three ``getVariables`` overloads)."""
        if component is None:
            result: dict[Variable, None] = {}
            hyper_vars = set(self._hyper_edges.values())
            for v in self._graph.vertices():
                if v not in hyper_vars:
                    result[v] = None
            for c in self._hyper_edges:
                for v in c.scope:
                    result[v] = None
            return list(result)
        if self.solver is not None:
            return self.solver.get_variables(component, *markings_to_exclude)
        filtered: list[Variable] = []
        for var in self.get_variables():
            if var.component is not None and component == var.component:
                excluded = var.marking is not None and any(
                    m == var.marking for m in markings_to_exclude
                )
                if not excluded:
                    filtered.append(var)
        return filtered

    def get_constraints(self) -> list[Constraint]:
        """All Constraints in the network, binary and n-ary alike."""
        result: list[Constraint] = [
            c for c in self._graph.edges() if isinstance(c, BinaryConstraint)
        ]
        result.extend(self._hyper_edges.keys())
        return result

    def contains_constraint(self, c: Constraint) -> bool:
        """True iff the given Constraint is in this network."""
        return self._graph.contains_edge(c) or c in self._hyper_edges

    def contains_variable(self, v: Variable | int) -> bool:
        """True iff the given Variable (or Variable id) is in this network."""
        if isinstance(v, int):
            return any(var.id == v for var in self._graph.vertices())
        return self._graph.contains_vertex(v)

    @property
    def edge_label(self) -> str:
        """Value drawn by ConstraintNetwork rendering methods (one line per constraint)."""
        return "".join(str(con) + "\n" for con in self.get_constraints())

    def __str__(self) -> str:
        return f"[ConstraintNetwork]: \n\tVertices: {self.get_variables()}\n\tConstriants: {self.get_constraints()}"

    def join(self, cn: ConstraintNetwork) -> None:
        """Merge the given ConstraintNetwork into this one."""
        for var in cn.get_variables():
            self.add_variable(var)
        for con in cn.get_constraints():
            self.add_constraint(con)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConstraintNetwork):
            return False
        for v in other.get_variables():
            if not self.contains_variable(v):
                return False
        for c in other.get_constraints():
            if not self.contains_constraint(c):
                return False
        for v in self.get_variables():
            if not other.contains_variable(v):
                return False
        for c in self.get_constraints():
            if not self.contains_constraint(c):
                return False
        return True

    # Java overrides equals() but not hashCode(), inheriting identity hashCode
    # (an inconsistency present in the original); mirror it rather than fix it.
    __hash__ = object.__hash__

    @property
    def weight(self) -> float:
        """Arbitrary weight attached to this network (e.g. by search heuristics)."""
        return self._weight

    @weight.setter
    def weight(self, value: float) -> None:
        """Set this network's weight."""
        self._weight = value

    def clone(self) -> ConstraintNetwork:
        """Return a new network of the same type containing the same Variables and Constraints."""
        ret = type(self)(self.solver)
        for v in self.get_variables():
            ret.add_variable(v)
        for con in self.get_constraints():
            ret.add_constraint(con)
        return ret

    def _get_native_variables(self) -> list[Variable]:
        """Variables that were first created as VariablePrototypes."""
        return list(self._substituted.keys())

    def find_hyperedge_constraint(self, dv: DummyVariable) -> Constraint | None:
        """The hyperedge Constraint whose DummyVariable hub is dv, if any."""
        for con, hub in self._hyper_edges.items():
            if hub == dv:
                return con
        return None

    def _undirected_neighbors(self, v: Variable) -> list[Variable]:
        result: dict[Variable, None] = {}
        for p in self._graph.predecessors(v):
            result[p] = None
        for s in self._graph.successors(v):
            result[s] = None
        return list(result)

    def get_neighboring_variables(self, var: Variable) -> list[Variable]:
        """Variables directly connected to var through one Constraint."""
        result: dict[Variable, None] = {}
        if isinstance(var, DummyVariable):
            return []
        for neighbor in self._undirected_neighbors(var):
            if isinstance(neighbor, DummyVariable):
                for nn in self._undirected_neighbors(neighbor):
                    result[nn] = None
                result.pop(var, None)
            else:
                result[neighbor] = None
        return list(result)

    def mask_constraints(self) -> None:
        """Mask every Constraint in this network."""
        for con in self.get_constraints():
            con.mask()

    def unmask_constraints(self) -> None:
        """Unmask every Constraint in this network."""
        for con in self.get_constraints():
            con.unmask()

    @property
    def unmasked_constraints(self) -> list[Constraint]:
        """All Constraints in this network that are not masked."""
        return [con for con in self.get_constraints() if not con.is_masked]

    @property
    def masked_constraints(self) -> list[Constraint]:
        """All Constraints in this network that are masked."""
        return [con for con in self.get_constraints() if con.is_masked]

    def save(self, path: str | Path) -> None:
        """Serialize this ConstraintNetwork to path (C10, replaces Java
        Serializable save/load)."""
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str | Path) -> ConstraintNetwork:
        """Deserialize a ConstraintNetwork previously written by :meth:`save`."""
        with open(path, "rb") as f:
            return pickle.load(f)


def mask_constraints(cons: list[Constraint]) -> None:
    """Mask every Constraint in the given list."""
    for con in cons:
        con.mask()


def unmask_constraints(cons: list[Constraint]) -> None:
    """Unmask every Constraint in the given list."""
    for con in cons:
        con.unmask()
