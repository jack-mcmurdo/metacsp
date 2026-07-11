"""Tests for metacsp.utility.graph (M1): parallel edges, removal cascades,
tree subtree extraction."""

from metacsp.utility.graph import DelegateTree, DirectedSparseMultigraph


def make_edge(name):
    return ("edge", name)


class TestDirectedSparseMultigraph:
    def test_add_vertices_and_edges(self):
        g = DirectedSparseMultigraph()
        assert g.add_vertex("a")
        assert not g.add_vertex("a")
        assert g.add_edge("e1", "a", "b")
        # endpoints auto-added
        assert g.contains_vertex("b")
        assert g.vertices() == ["a", "b"]
        assert g.edges() == ["e1"]
        assert g.source("e1") == "a"
        assert g.dest("e1") == "b"
        assert g.vertex_count == 2
        assert g.edge_count == 1

    def test_parallel_edges(self):
        g = DirectedSparseMultigraph()
        assert g.add_edge("e1", "a", "b")
        assert g.add_edge("e2", "a", "b")
        assert g.add_edge("e3", "b", "a")
        assert not g.add_edge("e1", "a", "b")  # same edge object rejected
        assert g.edge_count == 3
        assert g.find_edge_set("a", "b") == ["e1", "e2"]
        assert g.find_edge_set("b", "a") == ["e3"]
        assert g.find_edge_set("a", "missing") == []
        assert g.out_edges("a") == ["e1", "e2"]
        assert g.in_edges("a") == ["e3"]
        assert g.incident_edges("a") == ["e3", "e1", "e2"]
        # parallel edges give one distinct neighbor
        assert g.successors("a") == ["b"]
        assert g.predecessors("a") == ["b"]

    def test_remove_edge_keeps_vertices(self):
        g = DirectedSparseMultigraph()
        g.add_edge("e1", "a", "b")
        assert g.remove_edge("e1")
        assert not g.remove_edge("e1")
        assert g.contains_vertex("a") and g.contains_vertex("b")
        assert g.edges() == []
        assert g.find_edge_set("a", "b") == []

    def test_remove_vertex_cascades_to_incident_edges(self):
        g = DirectedSparseMultigraph()
        g.add_edge("e1", "a", "b")
        g.add_edge("e2", "b", "c")
        g.add_edge("e3", "c", "a")
        g.add_edge("e4", "b", "b")  # self-loop
        assert g.remove_vertex("b")
        assert not g.remove_vertex("b")
        assert not g.contains_vertex("b")
        assert g.vertices() == ["a", "c"]
        # every edge touching b is gone, e3 survives
        assert g.edges() == ["e3"]
        assert g.in_edges("a") == ["e3"]
        assert g.out_edges("c") == ["e3"]
        assert g.out_edges("a") == []

    def test_self_loop_incidence(self):
        g = DirectedSparseMultigraph()
        g.add_edge("e1", "a", "a")
        assert g.incident_edges("a") == ["e1"]  # once, not twice
        assert g.successors("a") == ["a"]
        assert g.predecessors("a") == ["a"]
        g.remove_vertex("a")
        assert g.edges() == []

    def test_insertion_order_is_deterministic(self):
        g = DirectedSparseMultigraph()
        for name in ["z", "m", "a", "q"]:
            g.add_vertex(name)
        assert g.vertices() == ["z", "m", "a", "q"]
        g.add_edge("e2", "m", "a")
        g.add_edge("e1", "z", "q")
        assert g.edges() == ["e2", "e1"]


class TestDelegateTree:
    def build_tree(self):
        #        root
        #       /    \
        #      a      b
        #     / \      \
        #    c   d      e
        t = DelegateTree()
        t.set_root("root")
        t.add_child("r-a", "root", "a")
        t.add_child("r-b", "root", "b")
        t.add_child("a-c", "a", "c")
        t.add_child("a-d", "a", "d")
        t.add_child("b-e", "b", "e")
        return t

    def test_structure(self):
        t = self.build_tree()
        assert t.root == "root"
        assert t.parent("root") is None
        assert t.parent("a") == "root"
        assert t.parent("c") == "a"
        assert t.parent_edge("c") == "a-c"
        assert t.children("root") == ["a", "b"]
        assert t.children("a") == ["c", "d"]
        assert t.children("c") == []
        assert t.is_leaf("c")
        assert not t.is_leaf("a")
        assert t.depth("root") == 0
        assert t.depth("b") == 1
        assert t.depth("d") == 2
        assert t.vertex_count == 6

    def test_add_child_errors(self):
        import pytest

        t = self.build_tree()
        with pytest.raises(ValueError):
            t.add_child("x", "missing-parent", "new")
        with pytest.raises(ValueError):
            t.add_child("x", "root", "a")  # already in the tree
        with pytest.raises(ValueError):
            t2 = DelegateTree()
            t2.set_root("r1")
            t2.set_root("r2")

    def test_remove_vertex_removes_subtree(self):
        t = self.build_tree()
        assert t.remove_vertex("a")
        assert not t.remove_vertex("a")
        assert t.vertices() == ["root", "b", "e"]
        assert not t.contains_vertex("c") and not t.contains_vertex("d")
        assert t.children("root") == ["b"]
        assert t.depth("e") == 2

    def test_remove_root_empties_tree(self):
        t = self.build_tree()
        assert t.remove_vertex("root")
        assert t.root is None
        assert t.vertices() == []
        assert t.edges() == []

    def test_subtree_extraction(self):
        t = self.build_tree()
        sub = t.subtree("a")
        assert sub.root == "a"
        assert sub.vertices() == ["a", "c", "d"]
        assert sub.edges() == ["a-c", "a-d"]
        assert sub.parent("a") is None
        assert sub.parent("c") == "a"
        assert sub.depth("d") == 1
        # original tree untouched
        assert t.parent("a") == "root"
        assert t.vertex_count == 6

    def test_subtree_of_leaf(self):
        t = self.build_tree()
        sub = t.subtree("e")
        assert sub.root == "e"
        assert sub.vertices() == ["e"]
        assert sub.edges() == []

    def test_add_subtree_grafts_onto_parent(self):
        t = DelegateTree()
        t.set_root("root")
        t.add_child("r-x", "root", "x")
        sub = DelegateTree()
        sub.set_root("a")
        sub.add_child("a-c", "a", "c")
        sub.add_child("a-d", "a", "d")
        t.add_subtree(sub, "root", "r-a")
        assert t.children("root") == ["x", "a"]
        assert t.parent("a") == "root"
        assert t.parent_edge("a") == "r-a"
        assert t.children("a") == ["c", "d"]
        assert t.depth("c") == 2
        # source tree untouched
        assert sub.root == "a"
        assert sub.parent("a") is None

    def test_add_subtree_of_leaf(self):
        t = DelegateTree()
        t.set_root("root")
        sub = DelegateTree()
        sub.set_root("leaf")
        t.add_subtree(sub, "root", "r-leaf")
        assert t.children("root") == ["leaf"]
        assert t.is_leaf("leaf")
