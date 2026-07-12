"""Port of multi/spatial/DE9IM/DE9IMRelationSolver.java.

The protected ``DE9IMRelationSolver(Class<?>[], Class<?>)`` constructor
(present in Java for subclassing, but never actually subclassed anywhere in
the codebase) passed reflection ``Class<?>`` objects through to
``ConstraintSolver``; per C5 it is dropped here in favor of the single
public no-arg constructor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.multi.spatial.de9im.de9im_relation import DE9IMRelation
from metacsp.multi.spatial.de9im.geometric_shape_variable import GeometricShapeVariable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.variable import Variable

__all__ = ["DE9IMRelationSolver"]


class DE9IMRelationSolver(ConstraintSolver):
    """A solver for constraint networks of :class:`DE9IMRelation`\\ s.

    Handles variables of type :class:`GeometricShapeVariable`, which
    represent points, line strings, or (not necessarily convex) polygons.
    """

    def __init__(self) -> None:
        super().__init__([DE9IMRelation], GeometricShapeVariable)
        self.set_options(
            ConstraintSolver.Options.DOMAINS_AUTO_INSTANTIATED,
            ConstraintSolver.Options.AUTO_PROPAGATE,
        )
        self.added_constraints: list[Constraint] | None = None
        self.removed_constraints: bool = False
        self.added_variables: bool = False
        self.removed_variables: bool = False

    def get_all_implicit_relations(self) -> list[Constraint]:
        """All the implicit :class:`DE9IMRelation`\\ s that exist among the
        variables in this solver's constraint network."""
        return self._get_all_implicit_relations(False)

    def get_all_implicit_rcc8_relations(self) -> list[Constraint]:
        """All the implicit :class:`DE9IMRelation`\\ s that exist among the
        variables in this solver's constraint network, limited to the eight
        Jointly Exclusive, Pairwise Disjoint relations (Contains, Within,
        Covers, CoveredBy, Disjoint, Overlaps, Touches, Equals) -- equivalent
        to the basic RCC8 relations (Cohn et al., 1997)."""
        return self._get_all_implicit_relations(True)

    def _get_all_implicit_relations(self, rcc8_relations: bool) -> list[Constraint]:
        cons: list[Constraint] = []
        vars_ = self.get_variables()
        for g1 in vars_:
            assert isinstance(g1, GeometricShapeVariable)
            for g2 in vars_:
                if g1 is not g2:
                    assert isinstance(g2, GeometricShapeVariable)
                    if not rcc8_relations:
                        rels = DE9IMRelation.get_relations(g1, g2)
                    else:
                        rels = DE9IMRelation.get_rcc8_relations(g1, g2)
                    con = DE9IMRelation(*rels)
                    con.from_ = g1
                    con.to = g2
                    cons.append(con)
        return cons

    def propagate(self) -> bool:
        if self.added_constraints is not None:
            for con in self.added_constraints:
                if isinstance(con, DE9IMRelation):
                    if not self._propagate_edge(con):
                        return False
            self.added_constraints = None
            return True
        if self.removed_constraints:
            self.logger.debug("Propagation skipped because only removing constraints")
            self.removed_constraints = False
            return True
        if self.added_variables:
            self.logger.debug("Propagation skipped because only adding variables")
            self.added_variables = False
            return True
        if self.removed_variables:
            self.logger.debug("Propagation skipped because only removing variables")
            self.removed_variables = False
            return True
        return self._propagate_full()

    def _propagate_edge(self, con: DE9IMRelation) -> bool:
        self.logger.debug("Edge propagation performed")
        g1 = con.from_
        g2 = con.to
        assert isinstance(g1, GeometricShapeVariable) and isinstance(g2, GeometricShapeVariable)
        # Are explicit (given) relations compatible with implicit ones?
        implicit_rels = set(DE9IMRelation.get_relations(g1, g2))
        for t in con.types:
            if t not in implicit_rels:
                return False
        return True

    def _propagate_full(self) -> bool:
        self.logger.debug("Full propagation performed")
        vars_ = self.get_variables()
        for g1 in vars_:
            assert isinstance(g1, GeometricShapeVariable)
            for g2 in vars_:
                if g1 is not g2:
                    assert isinstance(g2, GeometricShapeVariable)
                    # Are explicit (given) relations compatible with implicit ones?
                    implicit_rels = set(DE9IMRelation.get_relations(g1, g2))
                    for c in self.get_constraints(g1, g2):
                        assert isinstance(c, DE9IMRelation)
                        for t in c.types:
                            if t not in implicit_rels:
                                return False
        return True

    def _propagate_rcc8(self) -> bool:
        vars_ = self.get_variables()
        for g1 in vars_:
            assert isinstance(g1, GeometricShapeVariable)
            for g2 in vars_:
                if g1 is not g2:
                    assert isinstance(g2, GeometricShapeVariable)
                    # Are explicit (given, RCC8) relations compatible with implicit ones?
                    implicit_rels = set(DE9IMRelation.get_rcc8_relations(g1, g2))
                    for c in self.get_constraints(g1, g2):
                        assert isinstance(c, DE9IMRelation)
                        for t in c.types:
                            if not DE9IMRelation.is_rcc8_relation(t):
                                continue
                            if t not in implicit_rels:
                                return False
        return True

    def add_constraints_sub(self, c: list[Constraint]) -> bool:
        self.added_constraints = c
        return True

    def remove_constraints_sub(self, c: list[Constraint]) -> None:
        self.removed_constraints = True

    def create_variables_sub(self, num: int) -> list[Variable]:
        self.added_variables = True
        ret: list[Variable] = []
        for _ in range(num):
            ret.append(GeometricShapeVariable(self, self._ids))
            self._ids += 1
        return ret

    def remove_variables_sub(self, v: list[Variable]) -> None:
        self.removed_variables = True

    def register_value_choice_functions(self) -> None:
        pass
