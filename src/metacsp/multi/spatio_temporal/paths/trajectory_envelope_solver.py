"""Port of multi/spatioTemporal/paths/TrajectoryEnvelopeSolver.java.

The protected ``TrajectoryEnvelopeSolver(Class<?>[], Class<?>,
ConstraintSolver[], int[])`` constructor (present in Java for subclassing,
but never actually subclassed anywhere in the codebase) passed reflection
``Class<?>`` objects through to ``MultiConstraintSolver``; per C5 it is
dropped here (mirrors ``DE9IMRelationSolver``).

Several ``createEnvelopeNoParking``/``createEnvelopes`` overloads (which
differ only in whether a path/trajectory is given directly, as a single
file name, or as several file names to combine) are collapsed into single
Python methods dispatching on argument type, since Python has no method
overloading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Sequence, Union, cast

from metacsp.framework.multi.multi_constraint_solver import MultiConstraintSolver
from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.allen_interval.allen_interval_network_solver import AllenIntervalNetworkSolver
from metacsp.multi.spatial.de9im.de9im_relation import DE9IMRelation
from metacsp.multi.spatial.de9im.de9im_relation_solver import DE9IMRelationSolver
from metacsp.multi.spatio_temporal.paths.pose import Coordinate2D
from metacsp.multi.spatio_temporal.paths.pose_steering import PoseSteering
from metacsp.multi.spatio_temporal.paths.trajectory import Trajectory
from metacsp.multi.spatio_temporal.paths.trajectory_envelope import TrajectoryEnvelope
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds

if TYPE_CHECKING:
    from metacsp.framework.constraint_solver import ConstraintSolver
    from metacsp.multi.spatio_temporal.paths.pose import Pose

__all__ = ["TrajectoryEnvelopeSolver"]

Coordinate = Coordinate2D


class TrajectoryEnvelopeSolver(MultiConstraintSolver):
    """A MultiConstraintSolver for TrajectoryEnvelopes. Constraints of type
    AllenIntervalConstraint and DE9IMRelation can be added to
    TrajectoryEnvelopes."""

    DEFAULT_PARKING_DURATION: ClassVar[int] = 3000
    # Java's default footprint, 2.7 (w) x 6.6 (l) -- coordinate order
    # (frontLeft, frontRight, backLeft, backRight) copied verbatim from the
    # Java source. NOTE: this vertex order traces a self-intersecting
    # ("bowtie") quadrilateral rather than a simple rectangle (it should be
    # frontLeft, frontRight, backRight, backLeft to trace the perimeter in
    # order) -- an apparent bug in the upstream Java, replicated here for
    # fidelity (D4/C2: match observable Java behavior, not fix substantive
    # behavior bugs). GEOS -- like JTS, whose "side location conflict"
    # TopologyException message it shares verbatim -- raises a
    # ``GEOSException`` when asked to union geometries built from this
    # footprint; pass an explicit, validly-ordered ``footprint=`` to
    # :meth:`create_envelopes` instead.
    DEFAULT_FOOTPRINT: ClassVar[tuple[Coordinate, ...]] = (
        (5.3, 1.35),
        (5.3, -1.35),
        (-1.3, 1.35),
        (-1.3, -1.35),
    )

    def __init__(self, origin: int, horizon: int, max_trajectories: int | None = None) -> None:
        internal_solvers = self._create_internal_constraint_solvers(
            origin, horizon, -1 if max_trajectories is None else max_trajectories
        )
        super().__init__(
            [AllenIntervalConstraint, DE9IMRelation], TrajectoryEnvelope, internal_solvers, [1, 3]
        )

    @property
    def origin(self) -> int:
        """The origin of the underlying STP."""
        return self.get_temporal_solver().origin

    @property
    def horizon(self) -> int:
        """The horizon of the underlying STP."""
        return self.get_temporal_solver().horizon

    @staticmethod
    def _create_internal_constraint_solvers(
        origin: int, horizon: int, max_trajectories: int
    ) -> list[ConstraintSolver]:
        """Build the internal ActivityNetworkSolver and DE9IMRelationSolver."""
        if max_trajectories >= 1:
            activity_solver: ActivityNetworkSolver = ActivityNetworkSolver(
                origin, horizon, max_trajectories
            )
        else:
            activity_solver = ActivityNetworkSolver(origin, horizon)
        return [activity_solver, DE9IMRelationSolver()]

    def propagate(self) -> bool:
        """No-op: propagation is delegated entirely to the internal solvers."""
        return True

    def get_temporal_solver(self) -> AllenIntervalNetworkSolver:
        """This solver's internal AllenIntervalNetworkSolver (temporal-placement layer)."""
        return cast(
            ActivityNetworkSolver, self.constraint_solvers[0]
        ).get_allen_interval_network_solver()

    def get_spatial_solver(self) -> DE9IMRelationSolver:
        """This solver's internal DE9IMRelationSolver (spatial layer)."""
        return cast(DE9IMRelationSolver, self.constraint_solvers[1])

    def get_trajectory_envelopes(self, robot_id: int) -> list[TrajectoryEnvelope]:
        """All the TrajectoryEnvelopes in this solver's ConstraintNetwork
        pertaining to a particular robot."""
        return [
            te
            for v in self.get_variables()
            if (te := cast(TrajectoryEnvelope, v)).robot_id == robot_id
        ]

    def get_root_trajectory_envelopes(
        self, robot_id: int | None = None
    ) -> list[TrajectoryEnvelope]:
        """All TrajectoryEnvelopes that have no super-envelopes (optionally
        restricted to a given robot -- unifies Java's two overloads)."""
        ret = [
            te
            for v in self.get_variables()
            if not (te := cast(TrajectoryEnvelope, v)).has_super_envelope
        ]
        if robot_id is not None:
            ret = [te for te in ret if te.robot_id == robot_id]
        return ret

    def _make_envelope(
        self,
        robot_id: int,
        first_parking_duration: int,
        last_parking_duration: int,
        traj_robot: Trajectory,
        *footprint_coords: Coordinate,
    ) -> list[TrajectoryEnvelope]:
        """Build a driving envelope for ``traj_robot`` plus start/end parking envelopes
        joined by Meets constraints and minimum-duration constraints."""
        ret: list[TrajectoryEnvelope] = []

        te = cast(TrajectoryEnvelope, self.create_variable())
        parking_start = cast(TrajectoryEnvelope, self.create_variable())
        parking_end = cast(TrajectoryEnvelope, self.create_variable())

        te.component = f"Robot{robot_id}"
        te.symbolic_variable_activity.set_symbolic_domain("Driving")
        parking_start.component = f"Robot{robot_id}"
        parking_start.symbolic_variable_activity.set_symbolic_domain("Parking (initial)")
        parking_start.robot_id = robot_id
        parking_end.component = f"Robot{robot_id}"
        parking_end.symbolic_variable_activity.set_symbolic_domain("Parking (final)")
        parking_end.robot_id = robot_id

        cons_to_add: list[AllenIntervalConstraint] = []
        traj_envelope_robot = te
        traj_envelope_robot.set_footprint(*footprint_coords)
        traj_envelope_robot.trajectory = traj_robot
        traj_envelope_robot.robot_id = robot_id

        assert traj_envelope_robot.trajectory is not None
        parking_start_pose = traj_envelope_robot.trajectory.pose_steering[0].pose
        traj_start = Trajectory([parking_start_pose])
        parking_start.set_footprint(*footprint_coords)
        parking_start.trajectory = traj_start
        parking_start.refinable = False

        parking_end_pose = traj_envelope_robot.trajectory.pose_steering[-1].pose
        traj_end = Trajectory([parking_end_pose])
        parking_end.set_footprint(*footprint_coords)
        parking_end.trajectory = traj_end
        parking_end.refinable = False

        parking_meets_driving = AllenIntervalConstraint(AllenIntervalConstraint.Type.Meets)
        parking_meets_driving.from_ = parking_start
        parking_meets_driving.to = traj_envelope_robot
        cons_to_add.append(parking_meets_driving)

        driving_meets_parking = AllenIntervalConstraint(AllenIntervalConstraint.Type.Meets)
        driving_meets_parking.from_ = traj_envelope_robot
        driving_meets_parking.to = parking_end
        cons_to_add.append(driving_meets_parking)

        dur_first = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Duration, Bounds(first_parking_duration, APSPSolver.INF)
        )
        dur_first.from_ = parking_start
        dur_first.to = parking_start
        cons_to_add.append(dur_first)

        dur_last = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Duration, Bounds(last_parking_duration, APSPSolver.INF)
        )
        dur_last.from_ = parking_end
        dur_last.to = parking_end
        cons_to_add.append(dur_last)

        ret.append(parking_start)
        ret.append(traj_envelope_robot)
        ret.append(parking_end)

        self.add_constraints(*cons_to_add)

        return ret

    def create_envelope_no_parking(
        self,
        robot_id: int,
        path: Union[Sequence[PoseSteering], Sequence[str], str],
        symbol: str,
        *footprint_coords: Coordinate,
    ) -> TrajectoryEnvelope:
        """Port of the three ``createEnvelopeNoParking`` overloads
        (``PoseSteering[]``, ``String[]`` of path files, or a single
        ``String`` path file)."""
        traj_robot: Trajectory
        if isinstance(path, str):
            traj_robot = Trajectory(path)
        else:
            path_list = list(path)
            if path_list and isinstance(path_list[0], str):
                traj_robot = Trajectory(*path_list)
            else:
                traj_robot = Trajectory(path_list)
        te = cast(TrajectoryEnvelope, self.create_variable())
        te.component = f"Robot{robot_id}"
        te.symbolic_variable_activity.set_symbolic_domain(symbol)
        traj_envelope_robot = te
        traj_envelope_robot.set_footprint(*footprint_coords)
        traj_envelope_robot.trajectory = traj_robot
        traj_envelope_robot.robot_id = robot_id
        return traj_envelope_robot

    def create_parking_envelope(
        self,
        robot_id: int,
        parking_duration: int,
        parking_pose: Pose,
        location_name: str,
        *footprint_coords: Coordinate,
    ) -> TrajectoryEnvelope:
        """Create a standalone parking TrajectoryEnvelope with a minimum-duration constraint."""
        parking = cast(TrajectoryEnvelope, self.create_variable())
        parking.component = f"Robot{robot_id}"
        parking.symbolic_variable_activity.set_symbolic_domain(f"Parking ({location_name})")
        parking.robot_id = robot_id

        traj_parking = Trajectory([parking_pose])
        parking.set_footprint(*footprint_coords)
        parking.trajectory = traj_parking
        parking.refinable = False

        dur_parking = AllenIntervalConstraint(
            AllenIntervalConstraint.Type.Duration, Bounds(parking_duration, APSPSolver.INF)
        )
        dur_parking.from_ = parking
        dur_parking.to = parking

        self.add_constraints(dur_parking)

        return parking

    def create_envelopes(
        self,
        first_robot_id: int,
        *trajectories_or_files: Union[Trajectory, str],
        duration_first_parking: int = DEFAULT_PARKING_DURATION,
        duration_last_parking: int = DEFAULT_PARKING_DURATION,
        footprint: Sequence[Coordinate] | None = None,
    ) -> dict[int, list[TrajectoryEnvelope]]:
        """Create a TrajectoryEnvelope for each given Trajectory (or path
        file). Robot IDs are assigned starting from ``first_robot_id``.
        Creates three envelopes per Trajectory: the main TrajectoryEnvelope
        covering the path, plus start/end parking TrajectoryEnvelopes
        joined by Meets constraints.

        Unifies Java's four ``createEnvelopes`` overloads (``Trajectory
        ...``/``String ...`` inputs, each with or without explicit
        durations/footprint -- the defaults, 3000ms parking and the
        2.7x6.6 default footprint, match the Java no-duration/no-footprint
        overloads).
        """
        resolved_footprint = (
            footprint if footprint is not None else TrajectoryEnvelopeSolver.DEFAULT_FOOTPRINT
        )
        trajectories: list[Trajectory]
        if trajectories_or_files and isinstance(trajectories_or_files[0], str):
            trajectories = [Trajectory(cast(str, f)) for f in trajectories_or_files]
        else:
            trajectories = list(cast("tuple[Trajectory, ...]", trajectories_or_files))

        ret: dict[int, list[TrajectoryEnvelope]] = {}
        for i, traj in enumerate(trajectories):
            ret[i + first_robot_id] = self._make_envelope(
                i + first_robot_id,
                duration_first_parking,
                duration_last_parking,
                traj,
                *resolved_footprint,
            )
        return ret
