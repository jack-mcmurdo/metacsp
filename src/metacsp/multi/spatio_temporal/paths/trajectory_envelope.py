"""Port of multi/spatioTemporal/paths/TrajectoryEnvelope.java.

The Swing hierarchy viewer (``drawTrajectoryEnvelopeHierarchy``,
``TrajectoryEnvelopeHierarchyFrame``) is not ported -- see D10, skip list
(``utility/UI``).

Several Java methods are collapsed under one Python name because Python has
no method overloading; each collapse is documented at its definition:

- ``setFootprint``/``getFootprint``/``makeFootprint`` had five overloads
  total (direct :class:`~shapely.Polygon` assignment, ``Coordinate...``
  vertices, ``(width, length, dw, dl)`` dimensions, plus three near-duplicate
  static transform helpers) -- collapsed into :meth:`set_footprint`,
  :meth:`make_footprint`, and the two static helpers
  :meth:`make_footprint_at`/:meth:`make_footprint_for`.
- ``getGroundEnvelope(int)`` vs ``getGroundEnvelope(long)`` -- both take a
  bare Python ``int`` with no static-type distinction, so the ``long``
  (absolute-time) overload is renamed :meth:`get_ground_envelope_at_time`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Sequence, Union, cast

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry

from metacsp.exceptions import NoFootprintException
from metacsp.framework.multi.multi_variable import MultiVariable
from metacsp.multi.activity.activity import Activity
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.de9im.geometric_shape_variable import GeometricShapeVariable
from metacsp.multi.spatial.de9im.line_string_domain import LineStringDomain
from metacsp.multi.spatial.de9im.point_domain import PointDomain
from metacsp.multi.spatial.de9im.polygonal_domain import PolygonalDomain
from metacsp.multi.spatio_temporal.paths.pose import Coordinate2D
from metacsp.multi.spatio_temporal.paths.pose_steering import PoseSteering
from metacsp.multi.spatio_temporal.paths.trajectory import Trajectory
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.utility.graph import DelegateTree

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.framework.variable import Variable
    from metacsp.multi.allen_interval.allen_interval import AllenInterval

__all__ = ["TrajectoryEnvelope", "SpatialEnvelope"]

Coordinate = Coordinate2D


def _dist2d(a: Coordinate, b: Coordinate) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5


def _flatten_coord_args(args: Sequence[Any]) -> list[Coordinate]:
    """Java's ``Coordinate... coords`` accepts either individually-spread
    coordinates or a single array; support both calling conventions."""
    if (
        len(args) == 1
        and isinstance(args[0], (list, tuple))
        and args[0]
        and not isinstance(args[0][0], (int, float))
    ):
        return list(args[0])
    return list(args)


def _transform_footprint(footprint: Polygon, x: float, y: float, theta: float) -> BaseGeometry:
    """Rotate about the origin, then translate.

    Matches JTS ``new AffineTransformation().rotate(theta).translate(x,
    y)``: ``AffineTransformation.compose()`` (which ``translate`` calls)
    applies the *new* operation after the transformation accumulated so
    far, so the net effect is rotate-about-origin followed by translate.
    """
    rotated = affinity.rotate(footprint, theta, origin=(0, 0), use_radians=True)
    return affinity.translate(rotated, xoff=x, yoff=y)


def _union_footprints(footprints: Sequence[BaseGeometry]) -> BaseGeometry | None:
    one_poly: BaseGeometry | None = None
    prev_poly: BaseGeometry | None = None
    for rect in footprints:
        if one_poly is None:
            one_poly = rect
            prev_poly = rect
        else:
            assert prev_poly is not None
            aux_poly = prev_poly.union(rect)
            one_poly = one_poly.union(aux_poly.convex_hull)
            prev_poly = rect
    return one_poly


def _jts_coordinates(geom: BaseGeometry) -> list[Coordinate]:
    """Flatten a shapely geometry's coordinates the way JTS
    ``Geometry.getCoordinates()`` does: exterior ring then interior rings
    for polygons, recursively for collections."""
    if geom.is_empty:
        return []
    gtype = geom.geom_type
    if gtype == "Polygon":
        polygon = cast(Polygon, geom)
        coords = list(polygon.exterior.coords)
        for interior in polygon.interiors:
            coords.extend(interior.coords)
        return coords
    if gtype in ("Point", "LineString", "LinearRing"):
        return list(geom.coords)  # type: ignore[attr-defined]
    if hasattr(geom, "geoms"):
        coords = []
        for part in geom.geoms:  # type: ignore[attr-defined]
            coords.extend(_jts_coordinates(part))
        return coords
    return list(geom.coords)  # type: ignore[attr-defined]


class SpatialEnvelope:
    """Port of the nested class ``TrajectoryEnvelope.SpatialEnvelope``."""

    def __init__(self, path: list[PoseSteering], polygon: BaseGeometry, footprint: Polygon) -> None:
        self.path = path
        self.polygon = polygon
        self.footprint = footprint


class TrajectoryEnvelope(MultiVariable, Activity):
    """A MultiVariable composed of an Activity (temporal + symbolic part,
    internal variable 0), a reference-path GeometricShapeVariable (internal
    variable 1), a spatial-envelope GeometricShapeVariable (internal
    variable 2), and an inner-envelope GeometricShapeVariable (internal
    variable 3). Constraints of type AllenIntervalConstraint and
    DE9IMRelation can be added to TrajectoryEnvelopes."""

    RESOLUTION: ClassVar[int] = 1000

    def __init__(
        self,
        cs: ConstraintSolver,
        id: int,
        internal_solvers: list[ConstraintSolver],
        internal_vars: list[Variable],
    ) -> None:
        super().__init__(cs, id, internal_solvers, internal_vars)
        self._trajectory: Trajectory | None = None
        self._refinable = True
        self._super_envelope: TrajectoryEnvelope | None = None
        self._sub_envelopes: list[TrajectoryEnvelope] | None = None
        self._robot_id = -1
        self._footprint: Polygon | None = None
        self._inner_footprint: Polygon | None = None
        self._sequence_number_start = -1
        self._sequence_number_end = -1
        self._duration: AllenIntervalConstraint | None = None

    # --- footprint ---

    @property
    def footprint(self) -> Polygon | None:
        """This envelope's robot footprint polygon (local frame)."""
        return self._footprint

    @property
    def inner_footprint(self) -> Polygon | None:
        """This envelope's inner (conservative) robot footprint polygon (local frame), if set."""
        return self._inner_footprint

    def set_footprint(self, *args: Union[Coordinate, float, BaseGeometry]) -> None:
        """Port of the three ``setFootprint`` overloads: direct
        ``Polygon`` assignment, ``Coordinate...`` vertices (the common
        case), and ``(width, length, dw, dl)`` dimensions.

        Kept as an explicit method rather than a property setter because
        (like Java) it takes a variable number of arguments -- mirrors the
        existing ``set_symbolic_domain(*symbols)`` precedent.
        """
        if len(args) == 1 and isinstance(args[0], BaseGeometry):
            self._footprint = cast(Polygon, args[0])
            return
        if len(args) == 4 and all(isinstance(a, (int, float)) for a in args):
            width, length, dw, dl = cast("tuple[float, float, float, float]", args)
            self._footprint = TrajectoryEnvelope._make_rectangle_footprint(width, length, dw, dl)
            return
        self._footprint = TrajectoryEnvelope.create_footprint_polygon(*_flatten_coord_args(args))

    def set_inner_footprint(self, *coords: Coordinate) -> None:
        """Set this envelope's inner (conservative) footprint from vertex coordinates."""
        self._inner_footprint = TrajectoryEnvelope.create_footprint_polygon(
            *_flatten_coord_args(coords)
        )

    @staticmethod
    def _make_rectangle_footprint(width: float, length: float, dw: float, dl: float) -> Polygon:
        # JTS GeometricShapeFactory: setHeight(width) sets the Y-extent,
        # setWidth(length) sets the X-extent, setCentre(dl, dw).
        half_w = width / 2.0
        half_l = length / 2.0
        return box(dl - half_l, dw - half_w, dl + half_l, dw + half_w, ccw=True)

    @staticmethod
    def create_footprint_polygon(*coords: Coordinate) -> Polygon:
        """Build a closed Polygon from the given vertex coordinates."""
        ring = list(coords) + [coords[0]]
        return Polygon(ring)

    @staticmethod
    def make_footprint_at(footprint: Polygon, x: float, y: float, theta: float) -> BaseGeometry:
        """Port of the (near-duplicate) static overloads
        ``makeFootprint(double, double, double, Polygon)`` and
        ``getFootprint(Polygon, double, double, double)``, which compute
        the identical rotate-then-translate transform in the Java source."""
        return _transform_footprint(footprint, x, y, theta)

    @staticmethod
    def make_footprint_for(ps: PoseSteering, footprint: Polygon) -> BaseGeometry:
        """Port of the static overload ``makeFootprint(PoseSteering,
        Polygon)``."""
        return TrajectoryEnvelope.make_footprint_at(footprint, ps.x, ps.y, ps.theta)

    def make_footprint(self, ps: PoseSteering) -> BaseGeometry:
        """Port of the instance overloads ``makeFootprint(PoseSteering)``
        and ``makeFootprint(double, double, double)`` (the latter, using
        ``self.footprint``, is only ever called internally by the former in
        the Java source, so both collapse to this one method)."""
        assert self._footprint is not None
        return TrajectoryEnvelope.make_footprint_at(self._footprint, ps.x, ps.y, ps.theta)

    def make_inner_footprint(self, ps: PoseSteering) -> BaseGeometry:
        """Port of ``makeInnerFootprint(PoseSteering)`` /
        ``makeInnerFootprint(double, double, double)`` (see
        :meth:`make_footprint`)."""
        assert self._inner_footprint is not None
        return TrajectoryEnvelope.make_footprint_at(self._inner_footprint, ps.x, ps.y, ps.theta)

    # --- envelope hierarchy ---

    @property
    def envelope_hierarchy(self) -> DelegateTree[TrajectoryEnvelope, str]:
        """The tree of sub-envelopes rooted at this TrajectoryEnvelope."""
        ret: DelegateTree[TrajectoryEnvelope, str] = DelegateTree()
        ret.set_root(self)
        if self._sub_envelopes is not None:
            for sub_te in self._sub_envelopes:
                ret.add_subtree(sub_te.envelope_hierarchy, self, str(hash(sub_te)))
        return ret

    @property
    def info(self) -> str:
        """Human-readable summary of this envelope's ground envelopes and their temporal profile."""
        assert self._trajectory is not None
        te_dts = self._trajectory.dts
        te_cts = self.cts
        ret = f"{self}\n  Ground envelopes:"
        for te in self.ground_envelopes:
            ret += f"\n    {te}"
        ret += "\n\nSeq\tDT\tCT\n------------------------------------------\n"
        for i, dt in enumerate(te_dts):
            ret += f"{i}\t{dt:.2f} \t{te_cts[i]:.2f}"
            if i < len(te_dts) - 1:
                ret += "\n"
        return ret

    def add_sub_envelope(self, se: TrajectoryEnvelope) -> None:
        """Register a sub-TrajectoryEnvelope under this one."""
        if self._sub_envelopes is None:
            self._sub_envelopes = []
        self._sub_envelopes.append(se)

    @property
    def has_sub_envelopes(self) -> bool:
        """True iff this TrajectoryEnvelope has been split into sub-envelopes."""
        return bool(self._sub_envelopes)

    @property
    def sub_envelopes(self) -> list[TrajectoryEnvelope] | None:
        """This TrajectoryEnvelope's direct sub-envelopes, if any."""
        return self._sub_envelopes

    def _create_ct_vector(self) -> list[float]:
        return [-1.0] * self.path_length

    def get_time_to_estimate(self, seq_num_now: int, seq_num_to: int) -> float:
        """An estimate of the time to move between two path indices (see :meth:`Trajectory.get_time_to_estimate`)."""
        assert self._trajectory is not None
        return self._trajectory.get_time_to_estimate(seq_num_now, seq_num_to)

    def get_time_left_estimate(self, seq_num: int) -> float:
        """An estimate of the time left to move given the current path index."""
        assert self._trajectory is not None
        return self._trajectory.get_time_left_estimate(seq_num)

    def get_partial_time_left_estimate(self, seq_num: int) -> float:
        """Like :meth:`get_time_left_estimate`, restricted to the ground envelope at ``seq_num``."""
        return self.get_ground_envelope(seq_num).get_time_left_estimate(seq_num)

    @property
    def ground_envelopes(self) -> list[TrajectoryEnvelope]:
        """The ground TrajectoryEnvelopes of this TrajectoryEnvelope,
        ordered by increasing start time.

        A ``TreeSet`` in Java, ordered (and de-duplicated) by earliest
        start time; emulated here with a sorted list that drops later
        insertions whose EST compare-equal to an already-inserted one,
        exactly as ``TreeSet.add`` would.
        """
        ret: list[TrajectoryEnvelope] = []

        def insert(te: TrajectoryEnvelope) -> None:
            est = te.temporal_variable.est
            for i, existing in enumerate(ret):
                existing_est = existing.temporal_variable.est
                if est == existing_est:
                    return
                if est < existing_est:
                    ret.insert(i, te)
                    return
            ret.append(te)

        if self._sub_envelopes:
            for te in self._sub_envelopes:
                for g in te.ground_envelopes:
                    insert(g)
        else:
            insert(self)
        return ret

    def get_ground_envelope(self, seq_num: int) -> TrajectoryEnvelope:
        """The ground envelope containing the given path-sequence index."""
        if seq_num >= self.path_length:
            raise RuntimeError(
                f"Path length of {self} less than requested sequence number ({seq_num})"
            )
        counter = 0
        ret: TrajectoryEnvelope | None = None
        for te in self.ground_envelopes:
            if counter > seq_num:
                assert ret is not None
                return ret
            ret = te
            counter += te.path_length
        assert ret is not None
        return ret

    def get_ground_envelope_at_time(self, time: int) -> TrajectoryEnvelope | None:
        """Renamed from the Java overload ``getGroundEnvelope(long
        time)`` -- see module docstring."""
        if self.temporal_variable.est > time or self.temporal_variable.eet < time:
            return None
        if not self.has_sub_envelopes:
            return self
        for te in self.ground_envelopes:
            if te.temporal_variable.est <= time <= te.temporal_variable.eet:
                return te
        return None

    def get_closest_ground_envelope(self, time: int) -> TrajectoryEnvelope | None:
        """The ground envelope active at (or nearest before) the given time, if any."""
        if self.temporal_variable.est > time or self.temporal_variable.eet < time:
            return None
        if not self.has_sub_envelopes:
            return self
        envelopes = self.ground_envelopes
        for i, te in enumerate(envelopes):
            if te.temporal_variable.est <= time:
                if te.temporal_variable.eet >= time:
                    return te
                if i + 1 < len(envelopes) and envelopes[i + 1].temporal_variable.est > time:
                    return te
        return None

    @property
    def super_envelope(self) -> TrajectoryEnvelope | None:
        """The TrajectoryEnvelope this one is a sub-envelope of, if any."""
        return self._super_envelope

    @super_envelope.setter
    def super_envelope(self, super_envelope: TrajectoryEnvelope | None) -> None:
        """Set this envelope's super-envelope and recompute its sequence numbers."""
        self._super_envelope = super_envelope
        self._update_sequence_numbers()

    def get_pose_steering(self, time: int) -> PoseSteering:
        """The interpolated PoseSteering on this envelope's path at the given time."""
        assert self._trajectory is not None
        ps_list = self._trajectory.pose_steering
        start_time = self.temporal_variable.est
        end_time = self.temporal_variable.eet
        if time < start_time or time > end_time:
            return ps_list[-1]
        if self.reference_path_variable.shape_type is PointDomain:
            return ps_list[0]

        total = end_time - start_time
        so_far = time - start_time
        percent = so_far / total

        line_domain = cast(LineStringDomain, self.reference_path_variable.domain)
        tot_distance = line_domain.geometry.length
        scanned_distance = 0.0
        previous_ps: PoseSteering | None = None
        current_ps: PoseSteering | None = None
        previous_ratio = 0.0
        current_ratio = 0.0
        index = 0
        while scanned_distance / tot_distance < percent:
            previous_ratio = scanned_distance / tot_distance
            previous_ps = ps_list[index]
            index += 1
            current_ps = ps_list[index]
            scanned_distance += _dist2d(
                (current_ps.x, current_ps.y), (previous_ps.x, previous_ps.y)
            )
            current_ratio = scanned_distance / tot_distance
        if previous_ps is None:
            return ps_list[0]
        assert current_ps is not None
        ratio = (percent - previous_ratio) / (current_ratio - previous_ratio)
        return previous_ps.interpolate(current_ps, ratio)

    @property
    def cts(self) -> list[float]:
        """Per-path-point completion times: start/end time of each ground envelope, else -1."""
        ret = self._create_ct_vector()
        counter = 0
        for te in self.ground_envelopes:
            ret[counter] = te.temporal_variable.est / TrajectoryEnvelope.RESOLUTION
            ret[counter + te.path_length - 1] = (
                te.temporal_variable.eet / TrajectoryEnvelope.RESOLUTION
            )
            counter += te.path_length
        return ret

    @property
    def robot_id(self) -> int:
        """The id of the robot this envelope belongs to (-1 if unset)."""
        return self._robot_id

    @robot_id.setter
    def robot_id(self, robot_id: int) -> None:
        """Set the id of the robot this envelope belongs to."""
        self._robot_id = robot_id

    def _update_sequence_numbers(self) -> None:
        if not self.has_super_envelope:
            self._sequence_number_start = 0
            assert self._trajectory is not None
            self._sequence_number_end = len(self._trajectory.pose) - 1
        else:
            super_env = self
            while super_env.has_super_envelope:
                assert super_env._super_envelope is not None
                super_env = super_env._super_envelope
            assert super_env._trajectory is not None and self._trajectory is not None
            ps_super_env = super_env._trajectory.positions
            ps_this = self._trajectory.positions
            self._sequence_number_start = 0
            while ps_super_env[self._sequence_number_start] != ps_this[0]:
                self._sequence_number_start += 1
            self._sequence_number_end = (
                self._sequence_number_start + len(self._trajectory.positions) - 1
            )
            self._trajectory.update_sequence_numbers(
                self._sequence_number_start, self._sequence_number_end
            )

    @property
    def has_super_envelope(self) -> bool:
        """True iff this TrajectoryEnvelope is a sub-envelope of another."""
        return self._super_envelope is not None

    @property
    def refinable(self) -> bool:
        """True iff this envelope may still be split into sub-envelopes."""
        return self._refinable

    @refinable.setter
    def refinable(self, refinable: bool) -> None:
        """Set whether this envelope may still be split into sub-envelopes."""
        self._refinable = refinable

    def __lt__(self, other: Variable) -> bool:
        # Java's compareTo is an unfinished stub that always returns 0.
        return False

    def create_internal_constraints(self, variables: list[Variable]) -> list[Constraint] | None:
        """No internal constraints: the Activity, path, envelope, and inner-envelope parts
        are independent."""
        return None

    @property
    def domain(self) -> Any:
        """This envelope's domain, as a MultiDomain over its internal variables."""
        return super().domain

    @domain.setter
    def domain(self, d: Any) -> None:
        """Route a LineString/Point/Polygonal domain to the matching internal variable."""
        if isinstance(d, (LineStringDomain, PointDomain)):
            self.internal_variables[1].domain = d
        elif isinstance(d, PolygonalDomain):
            self.internal_variables[2].domain = d

    def __str__(self) -> str:
        ret = (
            f"TrajectoryEnvelope {self.id} (Robot {self._robot_id}, "
            f"SE {self.envelope_variable.id}) "
            f"[{self.sequence_number_start};{self.sequence_number_end}]"
        )
        symbols = self.symbols
        if symbols:
            ret += " " + "".join(symbols)
        return ret

    @property
    def temporal_variable(self) -> AllenInterval:
        """This envelope's temporal-placement internal variable."""
        return cast(SymbolicVariableActivity, self.internal_variables[0]).temporal_variable

    @property
    def reference_path_variable(self) -> GeometricShapeVariable:
        """This envelope's reference-path internal variable."""
        return cast(GeometricShapeVariable, self.internal_variables[1])

    @property
    def envelope_variable(self) -> GeometricShapeVariable:
        """This envelope's spatial-envelope internal variable."""
        return cast(GeometricShapeVariable, self.internal_variables[2])

    @property
    def internal_envelope_variable(self) -> GeometricShapeVariable:
        """This envelope's inner-envelope internal variable."""
        return cast(GeometricShapeVariable, self.internal_variables[3])

    @property
    def symbolic_variable_activity(self) -> SymbolicVariableActivity:
        """This envelope's temporal+symbolic Activity internal variable."""
        return cast(SymbolicVariableActivity, self.internal_variables[0])

    @property
    def symbols(self) -> list[str]:
        """This envelope's current symbolic value(s)."""
        return self.symbolic_variable_activity.symbols

    @property
    def variable(self) -> Variable:
        """This envelope's own Variable identity (itself)."""
        return self

    def get_sequence_number(self, coord: Coordinate) -> int:
        """The sequence number of the path point closest to a given coordinate."""
        assert self._trajectory is not None
        return self._trajectory.get_sequence_number(coord)

    # --- envelope geometry ---

    def get_partial_envelope_geometry(self, index_from: int, index_to: int) -> BaseGeometry:
        """The union of footprints swept between two path indices (inclusive)."""
        assert self._trajectory is not None
        ps_list = self._trajectory.pose_steering
        if (
            index_from > index_to
            or index_from < 0
            or index_from > len(ps_list) - 1
            or index_to < 0
            or index_to >= len(ps_list)
        ):
            raise RuntimeError("Indices incorrect!")
        footprints = [self.make_footprint(ps_list[i]) for i in range(index_from, index_to + 1)]
        one_poly = _union_footprints(footprints)
        assert one_poly is not None
        return one_poly

    def _envelope_coordinates(self) -> list[Coordinate]:
        assert self._trajectory is not None
        footprints = [self.make_footprint(ps) for ps in self._trajectory.pose_steering]
        one_poly = _union_footprints(footprints)
        assert one_poly is not None
        return _jts_coordinates(one_poly)

    def _inner_envelope_coordinates(self) -> list[Coordinate]:
        assert self._trajectory is not None
        footprints = [self.make_inner_footprint(ps) for ps in self._trajectory.pose_steering]
        one_poly = _union_footprints(footprints)
        assert one_poly is not None
        return _jts_coordinates(one_poly)

    @staticmethod
    def create_spatial_envelope(
        path: Sequence[PoseSteering], *footprint: Coordinate
    ) -> SpatialEnvelope:
        """Build a standalone SpatialEnvelope (path, swept geometry, footprint) for a path
        and footprint, without a backing TrajectoryEnvelope variable."""
        fp = TrajectoryEnvelope.create_footprint_polygon(*footprint)
        footprints = [TrajectoryEnvelope.make_footprint_for(ps, fp) for ps in path]
        one_poly = _union_footprints(footprints)
        assert one_poly is not None
        return SpatialEnvelope(list(path), one_poly, fp)

    @property
    def spatial_envelope(self) -> SpatialEnvelope:
        """This envelope's path, swept geometry, and footprint as a SpatialEnvelope."""
        geom = cast(PolygonalDomain, self.envelope_variable.domain).geometry
        assert self._trajectory is not None and self._footprint is not None
        return SpatialEnvelope(self._trajectory.pose_steering, geom, self._footprint)

    @property
    def envelope_bounding_box(self) -> Polygon:
        """Deprecated (mirrors Java's ``@Deprecated getEnvelopeBoundingBox``):
        the bounding polygon of this envelope's own geometry (**not** an
        axis-aligned bounding box, despite the name -- this is exactly what
        the Java source computes)."""
        return TrajectoryEnvelope.create_footprint_polygon(*self._envelope_coordinates())

    # --- trajectory ---

    @property
    def trajectory(self) -> Trajectory | None:
        """This envelope's Trajectory, if set."""
        return self._trajectory

    @trajectory.setter
    def trajectory(self, traj: Trajectory) -> None:
        """Set this envelope's Trajectory, building its swept geometry and duration constraint."""
        if self._footprint is None:
            raise NoFootprintException(
                f"No footprint set for {self}, please specify one before setting the trajectory."
            )
        self._create_outer_envelope(traj)
        if self._inner_footprint is not None:
            self._create_inner_envelope(traj)

    def _create_inner_envelope(self, traj: Trajectory) -> None:
        env = PolygonalDomain(self.internal_envelope_variable, self._inner_envelope_coordinates())
        self.internal_envelope_variable.domain = env

    def _create_outer_envelope(self, traj: Trajectory) -> None:
        self._trajectory = traj
        if len(traj.pose_steering) == 1:
            pd = PointDomain(self, traj.positions[0])
            self.domain = pd
        else:
            lsd = LineStringDomain(self, traj.positions)
            self.domain = lsd
        env = PolygonalDomain(self, self._envelope_coordinates())
        self.domain = env
        self.update_duration()
        self._update_sequence_numbers()

    def update_duration(self) -> None:
        """Impose a temporal constraint that models the minimum duration of
        this TrajectoryEnvelope, derived from the minimum transition times
        between path poses (deltaTs)."""
        assert self._trajectory is not None
        min_duration = 0
        for dt in self._trajectory.dts:
            # Java's `minDuration += dt*RESOLUTION` on a `long` accumulator
            # implicitly truncates towards zero on every iteration.
            min_duration = int(min_duration + dt * TrajectoryEnvelope.RESOLUTION)
        self._duration = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Duration, Bounds(min_duration, APSPSolver.INF)
        )
        self._duration.from_ = self
        self._duration.to = self
        con_add = self.constraint_solver.add_constraint(self._duration)
        if con_add:
            self.logger.debug("Added duration constraint %s", self._duration)
        else:
            raise RuntimeError(f"Failed to add duration constraint {self._duration}")

    @property
    def sequence_number_start(self) -> int:
        """Index of this envelope's first path point within its super-envelope, if any."""
        return self._sequence_number_start

    @property
    def sequence_number_end(self) -> int:
        """Index of this envelope's last path point within its super-envelope, if any."""
        return self._sequence_number_end

    @property
    def path_length(self) -> int:
        """Number of path points in this envelope's Trajectory."""
        assert self._trajectory is not None
        return len(self._trajectory.pose_steering)


TrajectoryEnvelope.SpatialEnvelope = SpatialEnvelope  # type: ignore[attr-defined]
