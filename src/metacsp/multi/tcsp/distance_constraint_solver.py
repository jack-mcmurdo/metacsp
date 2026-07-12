"""Port of multi/TCSP/DistanceConstraintSolver.java.

Note: ``propagate()``'s path-consistency tightening operates on a local
``_complete_network`` copy of DistanceConstraints and never writes the
tightened bounds back into the real network or the internal APSPSolver (this
matches the Java source precisely -- the actual bound propagation for added
constraints happens via APSPSolver, through DistanceConstraint's normal
lifting to SimpleDistanceConstraints; this method only additionally checks --
and, oddly, discards -- a stronger consistency signal).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.constraint_solver import ConstraintSolver
from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.tcsp.distance_constraint import DistanceConstraint
from metacsp.multi.tcsp.multi_time_point import MultiTimePoint
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import INF, Bounds

if TYPE_CHECKING:
    from metacsp.framework.variable import Variable

__all__ = ["DistanceConstraintSolver"]


class DistanceConstraintSolver(MultiConstraintSolver):
    """A TCSP (Temporal Constraint Satisfaction Problem) solver: a
    MultiConstraintSolver over MultiTimePoints/DistanceConstraints, backed by
    a single internal APSPSolver."""

    def __init__(self, origin: int, horizon: int) -> None:
        super().__init__([DistanceConstraint], MultiTimePoint, [APSPSolver(origin, horizon)], [1])
        self._complete_network: ConstraintNetwork | None = None
        internal_solver = cast(APSPSolver, self.constraint_solvers[0])
        self.source = MultiTimePoint(
            self, self._ids, self.constraint_solvers, [internal_solver.source]
        )
        self._ids += 1
        self.sink = MultiTimePoint(self, self._ids, self.constraint_solvers, [internal_solver.sink])
        self._ids += 1
        self.the_network.add_variable(self.source)
        self.the_network.add_variable(self.sink)
        self.set_options(MultiConstraintSolver.Options.ALLOW_INCONSISTENCIES)

    def _create_complete_network(self) -> None:
        self._complete_network = ConstraintNetwork(self)
        original_network = self.the_network
        for var in original_network.get_variables():
            self._complete_network.add_variable(var)
        vars_ = self._complete_network.get_variables()
        for i, vi in enumerate(vars_):
            for j, vj in enumerate(vars_):
                if i == j:
                    continue
                if original_network.get_constraint(vi, vj) is None:
                    if original_network.get_constraint(vj, vi) is not None:
                        orig = cast(DistanceConstraint, original_network.get_constraint(vj, vi))
                        orig_bounds = orig.bounds
                        # i --[10,20]--> j ==> i --(20)--> j + j --(-10)--> i
                        # j --[-20,-10]--> i ==> j --(-10)--> i + i --(20)--> j
                        inverse_bounds = [Bounds(-b.max, -b.min) for b in orig_bounds]
                        inverse = DistanceConstraint(*inverse_bounds)
                        inverse.from_ = vi
                        inverse.to = vj
                        self._complete_network.add_constraint(inverse)
                    else:
                        universal = DistanceConstraint(Bounds(-INF, INF))
                        universal.from_ = vi
                        universal.to = vj
                        self._complete_network.add_constraint(universal)
                else:
                    orig = cast(DistanceConstraint, original_network.get_constraint(vi, vj))
                    orig_bounds = orig.bounds
                    new_bounds = [Bounds(b.min, b.max) for b in orig_bounds]
                    copy = DistanceConstraint(*new_bounds)
                    copy.from_ = vi
                    copy.to = vj
                    self._complete_network.add_constraint(copy)

    def get_composition(self, c1: DistanceConstraint, c2: DistanceConstraint) -> DistanceConstraint:
        b1 = c1.bounds
        b2 = c2.bounds
        comp_bounds = [Bounds(x.min + y.min, x.max + y.max) for x in b1 for y in b2]

        to_remove = [
            comp_bounds[i]
            for i in range(len(comp_bounds))
            for j in range(len(comp_bounds))
            if i != j
            and comp_bounds[i].min >= comp_bounds[j].min
            and comp_bounds[i].max <= comp_bounds[j].max
        ]
        for b in to_remove:
            if b in comp_bounds:
                comp_bounds.remove(b)

        ret = DistanceConstraint(*comp_bounds)
        ret.from_ = c1.from_
        ret.to = c2.to
        return ret

    def get_intersection(
        self, c1: DistanceConstraint, c2: DistanceConstraint
    ) -> DistanceConstraint | None:
        if not (c1.from_ == c2.from_ and c1.to == c2.to):
            return None

        int_bounds: list[Bounds] = []
        for b1 in c1.bounds:
            for b2 in c2.bounds:
                if b1.is_intersecting(b2):
                    one_int = b1.intersect(b2)
                    assert one_int is not None
                    int_bounds.append(one_int)

        if not int_bounds:
            return None

        ret = DistanceConstraint(*int_bounds)
        ret.from_ = c1.from_
        ret.to = c1.to
        return ret

    def propagate(self) -> bool:
        # APSPSolver will also propagate what it can... but first, let's reduce these intervals!
        self._create_complete_network()
        assert self._complete_network is not None
        fixedpoint = False
        vars_ = self._complete_network.get_variables()
        while not fixedpoint:
            fixedpoint = True
            for k in range(len(vars_)):
                for i in range(len(vars_)):
                    if i == k:
                        continue
                    for j in range(len(vars_)):
                        if j == k or j == i:
                            continue
                        r_ij = cast(
                            DistanceConstraint,
                            self._complete_network.get_constraint(vars_[i], vars_[j]),
                        )
                        r_ik = cast(
                            DistanceConstraint,
                            self._complete_network.get_constraint(vars_[i], vars_[k]),
                        )
                        r_kj = cast(
                            DistanceConstraint,
                            self._complete_network.get_constraint(vars_[k], vars_[j]),
                        )
                        comp = self.get_composition(r_ik, r_kj)
                        inters = self.get_intersection(r_ij, comp)
                        if inters is None:
                            return False
                        b_orig = r_ij.bounds
                        b_new = inters.bounds
                        for one_orig in b_orig:
                            found = any(one_orig == one_new for one_new in b_new)
                            if not found:
                                self.logger.debug("Replaced %s with %s", r_ij, inters)
                                self._complete_network.remove_constraint(r_ij)
                                self._complete_network.add_constraint(inters)
                                fixedpoint = False
                                break
        return True

    def get_source(self) -> MultiTimePoint:
        return self.source

    def get_sink(self) -> MultiTimePoint:
        return self.sink
