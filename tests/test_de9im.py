"""Tests for metacsp.multi.spatial.de9im.

There is no Java JUnit test for this package (org.metacsp.multi.spatial.DE9IM
has no src/test counterpart); the fixtures and assertions below are derived
from what examples/TestDE9IMRelationSolver{,Simple}.java build and print:

- TestDE9IMRelationSolver.java builds a 10x10 square (g1), a 2x2 square (g2)
  touching g1's boundary near the origin (fully inside g1's closure but
  sharing part of its border), a line string (g3) crossing g1's boundary
  twice, and a point (g4) outside g1. It prints the implicit relations for
  every ordered pair, then tries (and prints the result of) adding an
  explicit ``Disjoint`` constraint between g1 and g2 -- which must fail
  since g1 actually *covers* g2 (they share boundary, so it is not a
  DE-9IM ``Contains``/strict RCC8 ``NTPP``-equivalent either).
- TestDE9IMRelationSolverSimple.java builds 3 variables with default
  (uninstantiated, empty-geometry) domains and tries to add a ``Contains``
  constraint between two of them -- which must fail, since an empty
  geometry contains nothing.
"""

from __future__ import annotations

from metacsp.multi.spatial.de9im import (
    DE9IMRelation,
    DE9IMRelationSolver,
    GeometricShapeVariable,
    LineStringDomain,
    PointDomain,
    PolygonalDomain,
)

Type = DE9IMRelation.Type


def _build_solver() -> tuple[DE9IMRelationSolver, list[GeometricShapeVariable]]:
    solver = DE9IMRelationSolver()
    vars_ = solver.create_variables(4)
    assert vars_ is not None

    g1, g2, g3, g4 = vars_
    assert isinstance(g1, GeometricShapeVariable)
    assert isinstance(g2, GeometricShapeVariable)
    assert isinstance(g3, GeometricShapeVariable)
    assert isinstance(g4, GeometricShapeVariable)

    g1.domain = PolygonalDomain(g1, [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
    g2.domain = PolygonalDomain(g2, [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)])
    g3.domain = LineStringDomain(g3, [(-40.0, -40.0), (0.0, 0.0), (10.0, 5.0), (11.0, 200.0)])
    g4.domain = PointDomain(g4, (-2.0, -2.0))

    return solver, [g1, g2, g3, g4]


class TestDE9IMRelationSolver:
    def test_implicit_relations_g1_covers_g2(self):
        solver, (g1, g2, g3, g4) = _build_solver()
        rels = set(DE9IMRelation.get_relations(g1, g2))
        # g2 lies inside g1 but shares boundary with it, so it is Covered
        # (not strictly Contained) -- see the Covers/CoveredBy vs.
        # Contains/Within boundary-intersection disambiguation in
        # DE9IMRelation._get_relations.
        assert rels == {Type.Covers, Type.Intersects}
        assert set(DE9IMRelation.get_relations(g2, g1)) == {Type.CoveredBy, Type.Intersects}

    def test_implicit_relations_g4_disjoint_from_g1(self):
        solver, (g1, g2, g3, g4) = _build_solver()
        assert DE9IMRelation.get_relations(g1, g4) == [Type.Disjoint]
        assert DE9IMRelation.get_relations(g4, g1) == [Type.Disjoint]

    def test_implicit_relations_g3_crosses_g1(self):
        solver, (g1, g2, g3, g4) = _build_solver()
        assert set(DE9IMRelation.get_relations(g1, g3)) == {Type.Intersects, Type.Crosses}

    def test_rcc8_relations_are_jepd_subset(self):
        solver, (g1, g2, g3, g4) = _build_solver()
        # RCC8 relations exclude Intersects/Crosses (not part of the JEPD
        # RCC8-equivalent subset).
        assert DE9IMRelation.get_rcc8_relations(g1, g2) == [Type.Covers]
        assert DE9IMRelation.get_rcc8_relations(g2, g1) == [Type.CoveredBy]
        assert DE9IMRelation.get_rcc8_relations(g1, g3) == []

    def test_get_all_implicit_relations_count(self):
        solver, vars_ = _build_solver()
        # 4 variables -> 4*3 = 12 ordered pairs.
        implicit = solver.get_all_implicit_relations()
        assert len(implicit) == 12
        rcc8 = solver.get_all_implicit_rcc8_relations()
        assert len(rcc8) == 12

    def test_explicit_disjoint_constraint_between_covering_shapes_fails(self):
        """Mirrors TestDE9IMRelationSolver.java: adding a Disjoint constraint
        between g1 and g2 must fail, since they actually Cover/CoveredBy."""
        solver, (g1, g2, g3, g4) = _build_solver()
        relation = DE9IMRelation(Type.Disjoint)
        relation.from_ = g1
        relation.to = g2
        assert solver.add_constraints(relation) is False

    def test_explicit_covers_constraint_succeeds(self):
        solver, (g1, g2, g3, g4) = _build_solver()
        relation = DE9IMRelation(Type.Covers)
        relation.from_ = g1
        relation.to = g2
        assert solver.add_constraints(relation) is True

    def test_shape_type(self):
        solver, (g1, g2, g3, g4) = _build_solver()
        assert g1.shape_type is PolygonalDomain
        assert g3.shape_type is LineStringDomain
        assert g4.shape_type is PointDomain


class TestDE9IMRelationSolverSimple:
    def test_contains_constraint_between_default_domains_fails(self):
        """Mirrors TestDE9IMRelationSolverSimple.java: all three variables
        keep their default (uninstantiated, empty-geometry) domain, so a
        Contains constraint between any pair must fail."""
        solver = DE9IMRelationSolver()
        vars_ = solver.create_variables(3)
        assert vars_ is not None

        relation1 = DE9IMRelation(Type.Contains)
        relation1.from_ = vars_[0]
        relation1.to = vars_[1]

        assert solver.add_constraints(relation1) is False

    def test_default_domain_is_empty_polygon(self):
        solver = DE9IMRelationSolver()
        (var,) = solver.create_variables(1)
        assert isinstance(var, GeometricShapeVariable)
        assert var.shape_type is PolygonalDomain
        assert var.domain.geometry.is_empty
