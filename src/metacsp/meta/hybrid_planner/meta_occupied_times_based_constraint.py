"""Port of meta/hybridPlanner/MetaOccupiedTimesBasedConstraint.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.meta.hybrid_planner.meta_occupied_constraint import MetaOccupiedConstraint
from metacsp.multi.allen_interval.allen_interval import AllenInterval
from metacsp.multi.spatial.rectangle_algebra.bounding_box import AwtRectangle, BoundingBox
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
    from metacsp.multi.temporal_rectangle_algebra.spatial_fluent import SpatialFluent

__all__ = ["MetaOccupiedTimesBasedConstraint"]


class MetaOccupiedTimesBasedConstraint(MetaOccupiedConstraint):
    """A :class:`MetaOccupiedConstraint` whose conflict test is based on the
    temporal boundedness of each SpatialFluent (rather than
    ``MetaOccupiedConstraint``'s unbounded-bounding-box test): a peak
    conflicts if it mixes a spatially fixed ("bounded", i.e. EST == LST)
    object with a spatially free ("unbounded") one and their padded
    almost-centre rectangles overlap."""

    def is_conflicting(
        self,
        peak: list[SymbolicVariableActivity],
        activity_to_fluent: dict[SymbolicVariableActivity, SpatialFluent],
    ) -> bool:
        if len(peak) == 1:
            return False

        from metacsp.meta.hybrid_planner.simple_hybrid_planner import SimpleHybridPlanner

        manipulation_area_encoding = cast(
            SimpleHybridPlanner, self.meta_cs
        ).manipulation_area_encoding
        for act in peak:
            if manipulation_area_encoding in act.symbolic_variable.symbols[0]:
                return False

        unboundedsf: list[SpatialFluent] = []
        boundedsf: list[SpatialFluent] = []
        # Here only whether the activity is temporally bounded or unbounded
        # (fixed vs. free start time) is considered.
        for act in peak:
            fluent = activity_to_fluent[act]
            if fluent.activity.temporal_variable.est == fluent.activity.temporal_variable.lst:
                boundedsf.append(fluent)
            else:
                unboundedsf.append(fluent)

        if not unboundedsf or not boundedsf:
            return False

        if unboundedsf[-1].name == boundedsf[-1].name:
            return False

        if unboundedsf[0].rectangular_region.is_unbounded():
            return False

        rec1 = _bounding_box_of(boundedsf[0]).get_almost_centre_rectangle()
        rec2 = _bounding_box_of(unboundedsf[0]).get_almost_centre_rectangle()

        r1new = AwtRectangle(
            rec1.min_x - self.pad,
            rec1.min_y - self.pad,
            rec1.width + 2 * self.pad,
            rec1.height + 2 * self.pad,
        )
        r2new = AwtRectangle(
            rec2.min_x - self.pad,
            rec2.min_y - self.pad,
            rec2.width + 2 * self.pad,
            rec2.height + 2 * self.pad,
        )

        if r1new.intersects(r2new):
            return True
        return False


def _bounding_box_of(fluent: SpatialFluent) -> BoundingBox:
    rr = fluent.rectangular_region
    interval_x = cast(AllenInterval, rr.internal_variables[0])
    interval_y = cast(AllenInterval, rr.internal_variables[1])
    return BoundingBox(
        Bounds(interval_x.est, interval_x.lst),
        Bounds(interval_x.eet, interval_x.let),
        Bounds(interval_y.est, interval_y.lst),
        Bounds(interval_y.eet, interval_y.let),
    )
