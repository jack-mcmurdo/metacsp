"""Directed multigraph and rooted tree replacing JUNG (D1).

Hand-written replacements for the two JUNG structures the framework uses:
``edu.uci.ics.jung.graph.DirectedSparseMultigraph`` (constraint networks) and
``edu.uci.ics.jung.graph.DelegateTree`` (meta-CSP search trees and
variable/solver hierarchies, incl. ``TreeUtils.getSubTree``).

All collections are insertion-ordered (C7) so iteration order — and hence any
solver decision that depends on it — is deterministic.
"""

from __future__ import annotations

from typing import Generic, Hashable, TypeVar

__all__ = ["DirectedSparseMultigraph", "DelegateTree"]

V = TypeVar("V", bound=Hashable)
E = TypeVar("E", bound=Hashable)


class DirectedSparseMultigraph(Generic[V, E]):
    """A directed graph that allows parallel edges; edge objects are unique keys.

    Mirrors the JUNG ``DirectedSparseMultigraph`` API used in ``framework/``.
    """

    def __init__(self) -> None:
        # vertex -> (in-edges dict, out-edges dict); dicts used as ordered sets
        self._in: dict[V, dict[E, None]] = {}
        self._out: dict[V, dict[E, None]] = {}
        # edge -> (source, dest)
        self._endpoints: dict[E, tuple[V, V]] = {}

    # --- vertices ---

    def add_vertex(self, v: V) -> bool:
        """Add a vertex; return False if it was already present."""
        if v in self._out:
            return False
        self._in[v] = {}
        self._out[v] = {}
        return True

    def remove_vertex(self, v: V) -> bool:
        """Remove a vertex and all its incident edges; return False if absent."""
        if v not in self._out:
            return False
        for e in list(self._in[v]) + list(self._out[v]):
            self.remove_edge(e)
        del self._in[v]
        del self._out[v]
        return True

    def contains_vertex(self, v: V) -> bool:
        return v in self._out

    def vertices(self) -> list[V]:
        return list(self._out)

    @property
    def vertex_count(self) -> int:
        return len(self._out)

    # --- edges ---

    def add_edge(self, e: E, src: V, dst: V) -> bool:
        """Add a directed edge from src to dst; return False if the edge object
        is already in the graph. Endpoints are added as vertices if absent
        (JUNG behavior)."""
        if e in self._endpoints:
            return False
        self.add_vertex(src)
        self.add_vertex(dst)
        self._endpoints[e] = (src, dst)
        self._out[src][e] = None
        self._in[dst][e] = None
        return True

    def remove_edge(self, e: E) -> bool:
        """Remove an edge; return False if absent. Endpoints stay in the graph."""
        if e not in self._endpoints:
            return False
        src, dst = self._endpoints.pop(e)
        del self._out[src][e]
        del self._in[dst][e]
        return True

    def contains_edge(self, e: E) -> bool:
        return e in self._endpoints

    def edges(self) -> list[E]:
        return list(self._endpoints)

    @property
    def edge_count(self) -> int:
        return len(self._endpoints)

    # --- incidence queries ---

    def in_edges(self, v: V) -> list[E]:
        return list(self._in[v])

    def out_edges(self, v: V) -> list[E]:
        return list(self._out[v])

    def incident_edges(self, v: V) -> list[E]:
        """In-edges followed by out-edges (each edge once; self-loops once)."""
        result = dict(self._in[v])
        result.update(self._out[v])
        return list(result)

    def source(self, e: E) -> V:
        return self._endpoints[e][0]

    def dest(self, e: E) -> V:
        return self._endpoints[e][1]

    def find_edge_set(self, src: V, dst: V) -> list[E]:
        """All edges directed from src to dst (JUNG ``findEdgeSet``)."""
        if src not in self._out or dst not in self._in:
            return []
        return [e for e in self._out[src] if self._endpoints[e][1] == dst]

    def predecessors(self, v: V) -> list[V]:
        """Distinct sources of v's in-edges, in insertion order."""
        return list({self._endpoints[e][0]: None for e in self._in[v]})

    def successors(self, v: V) -> list[V]:
        """Distinct destinations of v's out-edges, in insertion order."""
        return list({self._endpoints[e][1]: None for e in self._out[v]})


class DelegateTree(Generic[V, E]):
    """A rooted tree over a :class:`DirectedSparseMultigraph` delegate.

    Mirrors the JUNG ``DelegateTree`` API used by ``MetaConstraintSolver``
    search and the variable/solver hierarchies; :meth:`subtree` replaces JUNG
    ``TreeUtils.getSubTree``.
    """

    def __init__(self) -> None:
        self._graph: DirectedSparseMultigraph[V, E] = DirectedSparseMultigraph()
        self._root: V | None = None
        self._parent_edge: dict[V, E] = {}

    @property
    def root(self) -> V | None:
        return self._root

    def set_root(self, v: V) -> None:
        if self._root is not None:
            raise ValueError("Tree already has a root")
        self._graph.add_vertex(v)
        self._root = v

    def add_child(self, edge: E, parent: V, child: V) -> bool:
        """Attach child under parent via edge; return False if edge exists."""
        if not self._graph.contains_vertex(parent):
            raise ValueError(f"Tree must already contain parent {parent}")
        if self._graph.contains_vertex(child):
            raise ValueError(f"Tree already contains child {child}")
        if not self._graph.add_edge(edge, parent, child):
            return False
        self._parent_edge[child] = edge
        return True

    def remove_vertex(self, v: V) -> bool:
        """Remove v and its whole subtree (JUNG ``removeVertex``); False if absent."""
        if not self._graph.contains_vertex(v):
            return False
        for child in self.children(v):
            self.remove_vertex(child)
        self._graph.remove_vertex(v)
        self._parent_edge.pop(v, None)
        if v == self._root:
            self._root = None
        return True

    def contains_vertex(self, v: V) -> bool:
        return self._graph.contains_vertex(v)

    def vertices(self) -> list[V]:
        return self._graph.vertices()

    def edges(self) -> list[E]:
        return self._graph.edges()

    @property
    def vertex_count(self) -> int:
        return self._graph.vertex_count

    def parent(self, v: V) -> V | None:
        edge = self._parent_edge.get(v)
        if edge is None:
            return None
        return self._graph.source(edge)

    def parent_edge(self, v: V) -> E | None:
        return self._parent_edge.get(v)

    def children(self, v: V) -> list[V]:
        return self._graph.successors(v)

    def is_leaf(self, v: V) -> bool:
        return not self._graph.out_edges(v)

    def depth(self, v: V) -> int:
        """Number of edges from the root to v (root has depth 0)."""
        if not self._graph.contains_vertex(v):
            raise ValueError(f"Tree does not contain {v}")
        depth = 0
        node: V | None = v
        while node != self._root:
            assert node is not None
            node = self.parent(node)
            depth += 1
        return depth

    def subtree(self, v: V) -> DelegateTree[V, E]:
        """A new tree rooted at v containing v's whole subtree (JUNG
        ``TreeUtils.getSubTree``); vertices and edges are shared, not copied."""
        result: DelegateTree[V, E] = DelegateTree()
        result.set_root(v)
        stack = [v]
        while stack:
            node = stack.pop(0)
            for child in self.children(node):
                edge = self._parent_edge[child]
                result.add_child(edge, node, child)
                stack.append(child)
        return result
