"""Port of meta/hybridPlanner/ManipulationAreaDomain.java."""

from __future__ import annotations

from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.rectangle_algebra.rectangle_constraint import RectangleConstraint
from metacsp.multi.spatial.rectangle_algebra.unary_rectangle_constraint import (
    UnaryRectangleConstraint,
)
from metacsp.spatial.utility.spatial_rule import SpatialRule
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

__all__ = ["ManipulationAreaDomain"]

_Type = AllenIntervalConstraint.Type


def _default(t: AllenIntervalConstraint.Type) -> AllenIntervalConstraint:
    return AllenIntervalConstraint(t, *t.get_default_bounds())


def _overlap(t: AllenIntervalConstraint.Type, overlapped_max: Bounds) -> AllenIntervalConstraint:
    return AllenIntervalConstraint(
        t, Bounds(0, APSPSolver.INF), overlapped_max, Bounds(0, APSPSolver.INF)
    )


class ManipulationAreaDomain:
    """Port of ``ManipulationAreaDomain.java``: the fixed general spatial
    knowledge (as :class:`~metacsp.spatial.utility.spatial_rule.SpatialRule`
    lists) relating a robot arm's manipulation area, the placing area within
    it, the manipulated object, and the supporting table -- one rule set per
    (arm, direction) combination, e.g. ``"RA_north"``."""

    def __init__(self) -> None:
        self.man_area_size_x = Bounds(60, 60)
        self.man_area_size_y = Bounds(60, 60)

        self.placing_area_size_max = Bounds(40, 40)
        self.placing_area_size_min = Bounds(34, 34)

        self.overlapped_max = Bounds(30, 30)

        self._rules_hash_map: dict[str, list[SpatialRule]] = {}
        for relation in (
            "RA_north",
            "RA_east",
            "RA_south",
            "RA_west",
            "LA_north",
            "LA_east",
            "LA_south",
            "LA_west",
        ):
            self._rules_hash_map[relation] = self._get_spatial_knowledge(relation)

    def get_spatial_rules_by_relation(self, name: str) -> list[SpatialRule]:
        return self._rules_hash_map[name]

    def _get_spatial_knowledge(self, relation: str) -> list[SpatialRule]:
        srules: list[SpatialRule] = []

        r1 = SpatialRule(
            "manipulationArea",
            "manipulationArea",
            unary_ra_constraint=UnaryRectangleConstraint(
                UnaryRectangleConstraint.Type.Size, self.man_area_size_x, self.man_area_size_y
            ),
        )
        srules.append(r1)

        if "RA_south" in relation:
            r0 = self._placing_area_size_rule(max_first=True)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _overlap(_Type.OverlappedBy, self.overlapped_max), _default(_Type.MetBy)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    self.get_convexify_before_and_after(), _default(_Type.Meets)
                ),
            )
            srules.extend([r0, r2, r3, r4])
        elif "LA_south" in relation:
            r0 = self._placing_area_size_rule(max_first=True)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _overlap(_Type.Overlaps, self.overlapped_max), _default(_Type.MetBy)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    self.get_convexify_before_and_after(), _default(_Type.Meets)
                ),
            )
            srules.extend([r0, r2, r3, r4])
        elif "RA_west" in relation:
            r0 = self._placing_area_size_rule(max_first=False)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.MetBy), _overlap(_Type.Overlaps, self.overlapped_max)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.Meets), self.get_convexify_before_and_after()
                ),
            )
            srules.extend([r0, r2, r3, r4])
        elif "LA_west" in relation:
            r0 = self._placing_area_size_rule(max_first=False)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.MetBy), _overlap(_Type.OverlappedBy, self.overlapped_max)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.Meets), self.get_convexify_before_and_after()
                ),
            )
            srules.extend([r0, r2, r3, r4])
        elif "RA_north" in relation:
            r0 = self._placing_area_size_rule(max_first=True)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _overlap(_Type.Overlaps, self.overlapped_max), _default(_Type.Meets)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    self.get_convexify_before_and_after(), _default(_Type.MetBy)
                ),
            )
            srules.extend([r0, r2, r3, r4])
        elif "LA_north" in relation:
            r0 = self._placing_area_size_rule(max_first=True)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _overlap(_Type.OverlappedBy, self.overlapped_max), _default(_Type.Meets)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    self.get_convexify_before_and_after(), _default(_Type.MetBy)
                ),
            )
            srules.extend([r0, r2, r3, r4])
        elif "RA_east" in relation:
            r0 = self._placing_area_size_rule(max_first=False)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.Meets), _overlap(_Type.OverlappedBy, self.overlapped_max)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.MetBy), self.get_convexify_before_and_after()
                ),
            )
            srules.extend([r0, r2, r3, r4])
        elif "LA_east" in relation:
            r0 = self._placing_area_size_rule(max_first=False)
            r2 = SpatialRule(
                "placingArea",
                "manipulationArea",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.Meets), _overlap(_Type.Overlaps, self.overlapped_max)
                ),
            )
            r3 = self._object_to_placing_area_rule()
            r4 = SpatialRule(
                "manipulationArea",
                "table",
                binary_ra_constraint=RectangleConstraint(
                    _default(_Type.MetBy), self.get_convexify_before_and_after()
                ),
            )
            srules.extend([r0, r2, r3, r4])

        return srules

    def _placing_area_size_rule(self, max_first: bool) -> SpatialRule:
        x, y = (
            (self.placing_area_size_max, self.placing_area_size_min)
            if max_first
            else (self.placing_area_size_min, self.placing_area_size_max)
        )
        return SpatialRule(
            "placingArea",
            "placingArea",
            unary_ra_constraint=UnaryRectangleConstraint(UnaryRectangleConstraint.Type.Size, x, y),
        )

    def _object_to_placing_area_rule(self) -> SpatialRule:
        return SpatialRule(
            "object",
            "placingArea",
            binary_ra_constraint=RectangleConstraint(
                _default(_Type.During), _default(_Type.During)
            ),
        )

    def get_convexify_before_and_after(self) -> AllenIntervalConstraint:
        return AllenIntervalConstraint(
            _Type.Before,
            _Type.Meets,
            _Type.Overlaps,
            _Type.During,
            _Type.OverlappedBy,
            _Type.MetBy,
            _Type.After,
        )
