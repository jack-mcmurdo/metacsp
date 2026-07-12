"""Port of examples/multi/TestSpatioTemporalVariableSolver.java.

The Java original ends with ``JTSDrawingPanel.drawVariables(...)`` (Swing,
not ported -- see D10); dropped here.
"""

from __future__ import annotations

from metacsp.multi.spatial.de9im import (
    DE9IMRelation,
    DE9IMRelationSolver,
    LineStringDomain,
    PolygonalDomain,
)
from metacsp.multi.spatio_temporal.spatio_temporal_variable import SpatioTemporalVariable
from metacsp.multi.spatio_temporal.spatio_temporal_variable_solver import (
    SpatioTemporalVariableSolver,
)


def main() -> None:
    solver = SpatioTemporalVariableSolver(0, 1000)
    vars_ = solver.create_variables(3)
    assert vars_ is not None
    var0, var1 = vars_[0], vars_[1]
    assert isinstance(var0, SpatioTemporalVariable)
    assert isinstance(var1, SpatioTemporalVariable)

    var0.domain = PolygonalDomain(var0, [(0, 0), (10, 0), (10, 10), (0, 10)])
    var1.domain = LineStringDomain(var1, [(-10, -10), (0, 0), (20, 20), (30, 40)])

    relation = DE9IMRelation(DE9IMRelation.Type.Overlaps)
    relation.from_ = var0
    relation.to = var1

    print(f"Added {relation}?", solver.add_constraints(relation))

    de9im_solver = solver.constraint_solvers[1]
    assert isinstance(de9im_solver, DE9IMRelationSolver)
    print([str(r) for r in de9im_solver.get_all_implicit_relations()])


if __name__ == "__main__":
    main()
