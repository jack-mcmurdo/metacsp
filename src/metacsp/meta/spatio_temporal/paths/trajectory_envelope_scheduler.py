"""Port of meta/spatioTemporal/paths/TrajectoryEnvelopeScheduler.java.

The two ``TrajectoryEnvelopeScheduler(long origin, long horizon, long
animationTime)`` / ``TrajectoryEnvelopeScheduler(long origin, long horizon,
int maxTrajectories)`` constructor overloads (which Java's static
overload-resolution distinguishes by argument type at compile time -- both
are plain ints in Python) are collapsed into one constructor with two
independent optional keyword parameters, mirroring the ``num_activities``
collapse precedent in ``meta/symbols_and_time/scheduler.py`` (M15).

The two ``refineTrajectoryEnvelopesFixed`` overloads (``int maxSize`` vs.
``double[] proportions``) are likewise collapsed into one method dispatching
on the argument's runtime type (mirrors the ``TrajectoryEnvelopeSolver``
overload collapses, M14).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, Union, cast

from shapely.geometry import MultiPolygon, Point

from metacsp.framework.constraint_network import ConstraintNetwork
from metacsp.framework.meta.meta_constraint_solver import MetaConstraintSolver
from metacsp.meta.spatio_temporal.paths.map import Map
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.multi.spatial.de9im.de9im_relation import DE9IMRelation
from metacsp.multi.spatio_temporal.paths.pose_steering import PoseSteering
from metacsp.multi.spatio_temporal.paths.trajectory import Trajectory
from metacsp.multi.spatio_temporal.paths.trajectory_envelope import TrajectoryEnvelope
from metacsp.multi.spatio_temporal.paths.trajectory_envelope_solver import TrajectoryEnvelopeSolver
from metacsp.time.apsp_solver import APSPSolver
from metacsp.time.bounds import Bounds
from metacsp.utility.graph import DirectedSparseMultigraph

if TYPE_CHECKING:
    from metacsp.framework.meta.meta_variable import MetaVariable
    from metacsp.framework.variable import Variable

__all__ = ["TrajectoryEnvelopeScheduler"]

Type = AllenIntervalConstraint.Type


class _DependencyEdge:
    """A dependency-graph edge label: ``(waiting_point, threshold_point)``.

    Compares by identity, mirroring the Java source's ``new Integer[]
    {waitingPoint, thresholdPoint}`` edge label -- arrays don't override
    ``equals``/``hashCode``, so each edge object is a distinct graph key even
    if two edges happen to carry equal point values.
    """

    def __init__(self, waiting_point: int, threshold_point: int) -> None:
        self.waiting_point = waiting_point
        self.threshold_point = threshold_point

    def __repr__(self) -> str:
        return f"[{self.waiting_point}, {self.threshold_point}]"


class TrajectoryEnvelopeScheduler(MetaConstraintSolver):
    """A MetaConstraintSolver that backtracks over TrajectoryEnvelope
    conflicts (see the :class:`~metacsp.meta.spatio_temporal.paths.map.Map`
    MetaConstraint)."""

    MINIMUM_SIZE: int = 5

    def __init__(
        self,
        origin: int,
        horizon: int,
        animation_time: int = 0,
        max_trajectories: int | None = None,
    ) -> None:
        super().__init__(
            [AllenIntervalConstraint, DE9IMRelation],
            animation_time,
            TrajectoryEnvelopeSolver(origin, horizon, max_trajectories),
        )
        self.refined_with: dict[TrajectoryEnvelope, list[TrajectoryEnvelope]] = {}
        self._bt_counter = 0

    # --- dependency graph ---

    def get_current_dependencies(
        self,
    ) -> DirectedSparseMultigraph[TrajectoryEnvelope, _DependencyEdge]:
        """The dependency graph of TrajectoryEnvelopes from the resolving
        constraints added by this TrajectoryEnvelopeScheduler.

        Returns a directed graph where each edge (x, y) has a label
        {p1, p2} indicating that robot x.robot_id has to wait at path point
        p1 for robot y.robot_id to reach path point p2.
        """
        dep_graph: DirectedSparseMultigraph[TrajectoryEnvelope, _DependencyEdge] = (
            DirectedSparseMultigraph()
        )
        cn = self.constraint_solvers[0].constraint_network
        cons = cn.get_constraints()
        for con in cons:
            if isinstance(con, AllenIntervalConstraint):
                if con.types[0] is Type.BeforeOrMeets:
                    # The two TEs involved in the constraint.
                    must_wait_to_start = cast(TrajectoryEnvelope, con.to)
                    must_finish_before_other_can_start = cast(TrajectoryEnvelope, con.from_)
                    waiting_envelope: TrajectoryEnvelope | None = None

                    # Find waiting_envelope = previous of must_wait_to_start.
                    root = must_wait_to_start
                    while root.has_super_envelope:
                        assert root.super_envelope is not None
                        root = root.super_envelope
                    for dep_var in root.recursively_dependent_variables:
                        dep_te = cast(TrajectoryEnvelope, dep_var)
                        if (
                            not dep_te.has_sub_envelopes
                            and dep_te.trajectory is not None
                            and dep_te.trajectory.sequence_number_end
                            == must_wait_to_start.sequence_number_start - 1
                        ):
                            waiting_envelope = dep_te
                            break

                    # Calculate waiting points.
                    assert must_finish_before_other_can_start.trajectory is not None
                    threshold_point = (
                        must_finish_before_other_can_start.trajectory.sequence_number_end
                    )
                    waiting_point: int

                    # If there was no previous envelope, then make the robot
                    # stay in the start point of this one.
                    if waiting_envelope is None:
                        assert must_wait_to_start.trajectory is not None
                        waiting_point = must_wait_to_start.trajectory.sequence_number_start
                        waiting_envelope = must_wait_to_start
                    else:
                        assert waiting_envelope.trajectory is not None
                        waiting_point = waiting_envelope.trajectory.sequence_number_end

                    # Add edge in dep graph.
                    dep_graph.add_vertex(waiting_envelope)
                    dep_graph.add_vertex(must_finish_before_other_can_start)
                    dep_graph.add_edge(
                        _DependencyEdge(waiting_point, threshold_point),
                        waiting_envelope,
                        must_finish_before_other_can_start,
                    )
        return dep_graph

    # --- backtracking search hooks ---

    def pre_backtrack(self) -> None:
        """No-op: TrajectoryEnvelopeScheduler needs no extra bookkeeping before branching."""
        pass

    def retract_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> None:
        """No-op: TrajectoryEnvelopeScheduler needs no extra bookkeeping when retracting."""
        pass

    def add_resolver_sub(
        self, meta_variable: ConstraintNetwork, meta_value: ConstraintNetwork
    ) -> bool:
        """Always True: resolvers are always accepted before ground-CSP propagation."""
        return True

    @property
    def bt_counter(self) -> int:
        """Number of backtracking steps taken so far."""
        return self._bt_counter

    def post_backtrack(self, mv: MetaVariable) -> None:
        """Increment the backtracking step counter."""
        self._bt_counter += 1

    def get_upper_bound(self) -> float:
        """Always 0.0: TrajectoryEnvelopeScheduler does not support branch-and-bound optimization."""
        return 0.0

    def set_upper_bound(self) -> None:
        """No-op: TrajectoryEnvelopeScheduler does not support branch-and-bound optimization."""
        pass

    def get_lower_bound(self) -> float:
        """Always 0.0: TrajectoryEnvelopeScheduler does not support branch-and-bound optimization."""
        return 0.0

    def set_lower_bound(self) -> None:
        """No-op: TrajectoryEnvelopeScheduler does not support branch-and-bound optimization."""
        pass

    def has_conflict_clause(self, meta_value: ConstraintNetwork) -> bool:
        """Always False: TrajectoryEnvelopeScheduler does not support branch-and-bound optimization."""
        return False

    def reset_false_clause(self) -> None:
        """No-op: TrajectoryEnvelopeScheduler does not support branch-and-bound optimization."""
        pass

    # --- refinement ---

    def refine_trajectory_envelopes_fixed(
        self, max_size_or_proportions: Union[int, Sequence[float]]
    ) -> ConstraintNetwork:
        """Split every refinable TrajectoryEnvelope into fixed-size pieces
        (an ``int`` ``max_size``) or into pieces whose lengths are given as
        fractions of the whole path (a ``Sequence[float]`` of
        ``proportions``, which must sum to 1.0)."""
        ret = ConstraintNetwork(None)

        use_max_size = isinstance(max_size_or_proportions, int)
        max_size = 0
        proportions: list[float] | None = None
        if use_max_size:
            max_size = cast(int, max_size_or_proportions)
        else:
            proportions = list(cast(Sequence[float], max_size_or_proportions))
            total = sum(proportions)
            if abs(total - 1.0) > 0.00001:
                raise RuntimeError(
                    f"Proportions given for refinement must sum up to 1.0: {proportions}"
                )

        solver = cast(TrajectoryEnvelopeSolver, self.constraint_solvers[0])
        vars_ = solver.get_variables()
        for var in vars_:
            new_trajectories: list[Trajectory] = []
            te = cast(TrajectoryEnvelope, var)
            if te.refinable:
                te.refinable = False
                if (
                    not te.has_sub_envelopes
                    and te.trajectory is not None
                    and len(te.trajectory.pose) > 3
                ):
                    self.logger.info("Refining %s", te)
                    traj = te.trajectory
                    so_far = 0
                    if use_max_size:
                        while so_far < len(traj.pose):
                            piece_length = min(max_size, len(traj.pose) - so_far)
                            if piece_length == 0:
                                break
                            new_trajectories.append(self._make_piece(traj, so_far, piece_length))
                            so_far += piece_length
                    else:
                        assert proportions is not None
                        for i, part in enumerate(proportions):
                            piece_length = int(len(traj.pose) * part)
                            if i == len(proportions) - 1:
                                piece_length = len(traj.pose) - so_far
                            if piece_length == 0:
                                break
                            new_trajectories.append(self._make_piece(traj, so_far, piece_length))
                            so_far += piece_length

                if new_trajectories:
                    self._add_refined_sub_envelopes(te, new_trajectories, ret)

        if ret.get_constraints():
            if not solver.add_constraints(*ret.get_constraints()):
                raise RuntimeError("Failed to add temporal constraints in refinement!")
        self._recompute_usages()
        return ret

    @staticmethod
    def _make_piece(traj: Trajectory, so_far: int, piece_length: int) -> Trajectory:
        piece_poses = traj.pose[so_far : so_far + piece_length]
        dts = traj.dts[so_far : so_far + piece_length]
        piece = Trajectory(piece_poses)
        piece.dts = dts
        return piece

    def _add_refined_sub_envelopes(
        self,
        te: TrajectoryEnvelope,
        new_trajectories: list[Trajectory],
        ret: ConstraintNetwork,
    ) -> None:
        solver = cast(TrajectoryEnvelopeSolver, self.constraint_solvers[0])
        new_trajectory_envelopes: list[TrajectoryEnvelope] = []
        new_vars = solver.create_variables(len(new_trajectories))
        assert new_vars is not None
        for i, new_var in enumerate(new_vars):
            one_te = cast(TrajectoryEnvelope, new_var)
            one_te.component = te.component
            one_te.symbolic_variable_activity.set_symbolic_domain(*te.symbols)
            assert te.footprint is not None
            one_te.set_footprint(te.footprint)
            one_te.refinable = False
            one_te.trajectory = new_trajectories[i]
            one_te.super_envelope = te
            one_te.robot_id = te.robot_id
            te.add_sub_envelope(one_te)
            te.add_dependent_variables(one_te)
            new_trajectory_envelopes.append(one_te)

        starts = AllenIntervalConstraint(Type.Starts)
        starts.from_ = new_trajectory_envelopes[0]
        starts.to = te
        ret.add_constraint(starts)

        finishes = AllenIntervalConstraint(Type.Finishes, Bounds(1, APSPSolver.INF))
        finishes.from_ = new_trajectory_envelopes[-1]
        finishes.to = te
        ret.add_constraint(finishes)

        for i in range(len(new_trajectory_envelopes) - 1):
            from_te = new_trajectory_envelopes[i]
            to_te = new_trajectory_envelopes[i + 1]
            assert from_te.trajectory is not None
            ttt = from_te.trajectory.dts[-1]
            ttt_long = int(TrajectoryEnvelope.RESOLUTION * ttt)
            if ttt_long == 0:
                raise RuntimeError(f"Before bounds are 0! {ttt}")
            before = AllenIntervalConstraint(Type.Before, Bounds(ttt_long, ttt_long))
            before.from_ = from_te
            before.to = to_te
            ret.add_constraint(before)

    def refine_trajectory_envelopes(self) -> ConstraintNetwork:
        """Refine the TrajectoryEnvelopes maintained by the
        TrajectoryEnvelopeSolver underlying this scheduler, splitting
        TrajectoryEnvelopes that overlap in space.

        Returns a ConstraintNetwork containing the set of
        TrajectoryEnvelopes into which the existing TrajectoryEnvelopes
        were refined (empty if they cannot be refined any further).
        """
        ret = ConstraintNetwork(None)

        done = False
        while not done:
            done = True
            vars_one_iteration = self.constraint_solvers[0].get_variables()
            for i in range(len(vars_one_iteration) - 1):
                for j in range(i + 1, len(vars_one_iteration)):
                    te1 = cast(TrajectoryEnvelope, vars_one_iteration[i])
                    te2 = cast(TrajectoryEnvelope, vars_one_iteration[j])

                    if te1 not in self.refined_with:
                        self.refined_with[te1] = []
                    if te2 not in self.refined_with:
                        self.refined_with[te2] = []

                    te1_has_sub = te1.has_sub_envelopes
                    te2_has_sub = te2.has_sub_envelopes
                    if te1.robot_id != te2.robot_id:
                        shape1 = te1.envelope_variable.domain.geometry
                        shape2 = te2.envelope_variable.domain.geometry
                        if shape1.intersects(shape2):
                            if (
                                not te2_has_sub
                                and te1.refinable
                                and te2 not in self.refined_with[te1]
                            ):
                                ref1 = self._refine_trajectory_envelopes(te1, te2)
                                self.refined_with[te1].append(te2)
                                ret.join(ref1)
                                done = False
                            if (
                                not te1_has_sub
                                and te2.refinable
                                and te1 not in self.refined_with[te2]
                            ):
                                ref2 = self._refine_trajectory_envelopes(te2, te1)
                                self.refined_with[te2].append(te1)
                                ret.join(ref2)
                                done = False
        self._recompute_usages()
        return ret

    def _recompute_usages(self) -> None:
        meta_constraint = cast(Map, self.meta_constraints[0])
        for v in self.constraint_solvers[0].get_variables():
            te = cast(TrajectoryEnvelope, v)
            meta_constraint.remove_usage(te)
            self.logger.debug("Removed usage of %s", te)
        for v in self.constraint_solvers[0].get_variables():
            te = cast(TrajectoryEnvelope, v)
            if not te.has_super_envelope:
                for dep_var in te.recursively_dependent_variables:
                    sub_te = cast(TrajectoryEnvelope, dep_var)
                    if not sub_te.has_sub_envelopes:
                        meta_constraint.set_usage(sub_te)
                        self.logger.debug("Set usage of %s", sub_te)

    def refine_trajectory_envelopes_light(self) -> ConstraintNetwork:
        """Refine the TrajectoryEnvelopes maintained by the
        TrajectoryEnvelopeSolver underlying this scheduler, without
        actually splitting TrajectoryEnvelopes."""
        ret = ConstraintNetwork(None)
        meta_constraint = cast(Map, self.meta_constraints[0])
        for v in self.constraint_solvers[0].get_variables():
            te = cast(TrajectoryEnvelope, v)
            if not te.has_super_envelope:
                for gte in te.ground_envelopes:
                    meta_constraint.set_usage(gte)
        return ret

    def _refine_trajectory_envelopes(
        self, var1: TrajectoryEnvelope, var2: TrajectoryEnvelope
    ) -> ConstraintNetwork:
        solver = cast(TrajectoryEnvelopeSolver, self.constraint_solvers[0])
        to_return = ConstraintNetwork(None)

        if var1.path_length < TrajectoryEnvelopeScheduler.MINIMUM_SIZE:
            return to_return

        se1 = cast(TrajectoryEnvelope, var1).envelope_variable.domain.geometry
        se2 = cast(TrajectoryEnvelope, var2).envelope_variable.domain.geometry
        intersection = se1.intersection(se2)
        use_default_envelope_chunks = False

        if not intersection.is_valid:
            intersection = intersection.symmetric_difference(intersection.boundary)
            self.logger.info("Intersection %s with %s invalid - fixing", var1, var2)

        if isinstance(intersection, MultiPolygon):
            self.logger.info(
                "Intersection %s with %s too complex - using default segmentation", var1, var2
            )
            use_default_envelope_chunks = True

        in_ = False
        count_in = 0
        assert var1.trajectory is not None
        for i in range(var1.path_length):
            coord = var1.trajectory.positions[i]
            point = Point(coord)
            if intersection.contains(point) and not in_:
                in_ = True
                count_in += 1
                if count_in > 1:
                    self.logger.info(
                        "Reference path of %s enters intersection with %s multiple "
                        "times - using default segmentation",
                        var1,
                        var2,
                    )
                    use_default_envelope_chunks = True
                    break
            if not intersection.contains(point):
                in_ = False

        area_difference = (
            intersection.symmetric_difference(intersection.boundary).union(se1).area - se1.area
        )
        if area_difference > 0.001:
            self.logger.info(
                "Intersection %s with %s seems corrupt (area increased by %s) - skipping ",
                var1,
                var2,
                area_difference,
            )
            use_default_envelope_chunks = True

        var1sec1: list[PoseSteering] = []
        var1sec2: list[PoseSteering] = []
        var1sec3: list[PoseSteering] = []

        skip_sec1 = False
        skip_sec3 = False

        if use_default_envelope_chunks:
            percentage_chunk_one = 0.30
            percentage_chunk_two = 0.40
            for i in range(var1.path_length):
                ps = var1.trajectory.pose_steering[i]
                if i < var1.path_length * percentage_chunk_one:
                    var1sec1.append(ps)
                elif i < var1.path_length * (percentage_chunk_one + percentage_chunk_two):
                    var1sec2.append(ps)
                else:
                    var1sec3.append(ps)
            self.logger.info(
                "Using default chunk sizes %d / %d / %d",
                len(var1sec1),
                len(var1sec2),
                len(var1sec3),
            )
        else:
            for i in range(var1.path_length):
                ps = var1.trajectory.pose_steering[i]
                fp = var1.make_footprint(ps)
                if not intersection.intersects(fp) and not var1sec2:
                    var1sec1.append(ps)
                elif intersection.intersects(fp):
                    var1sec2.append(ps)
                elif not intersection.intersects(fp) and var1sec2:
                    var1sec3.append(ps)

            # Add to start.
            done = False
            while not done:
                try:
                    last_poly_sec1 = var1.make_footprint(var1sec1[-1])
                    if last_poly_sec1.disjoint(se2):
                        done = True
                    else:
                        var1sec2.insert(0, var1sec1.pop())
                except IndexError:
                    skip_sec1 = True
                    done = True
            # If sec1 emptied, remove it.
            if len(var1sec1) < TrajectoryEnvelopeScheduler.MINIMUM_SIZE:
                while var1sec1:
                    var1sec2.insert(0, var1sec1.pop())
                skip_sec1 = True

            # Add to end.
            done = False
            while not done:
                try:
                    first_poly_sec3 = var1.make_footprint(var1sec3[0])
                    if first_poly_sec3.disjoint(se2):
                        done = True
                    else:
                        var1sec2.append(var1sec3.pop(0))
                except IndexError:
                    skip_sec3 = True
                    done = True
            # If sec3 emptied, remove it.
            if len(var1sec3) < TrajectoryEnvelopeScheduler.MINIMUM_SIZE:
                while var1sec3:
                    var1sec2.append(var1sec3.pop(0))
                skip_sec3 = True

            if len(var1sec2) < TrajectoryEnvelopeScheduler.MINIMUM_SIZE:
                if len(var1sec1) > TrajectoryEnvelopeScheduler.MINIMUM_SIZE:
                    var1sec2.insert(0, var1sec1.pop())
                elif len(var1sec3) > TrajectoryEnvelopeScheduler.MINIMUM_SIZE:
                    var1sec2.append(var1sec3.pop(0))

            if (
                (skip_sec1 and skip_sec3)
                or (not skip_sec1 and len(var1sec1) < TrajectoryEnvelopeScheduler.MINIMUM_SIZE)
                or (not skip_sec3 and len(var1sec3) < TrajectoryEnvelopeScheduler.MINIMUM_SIZE)
                or len(var1sec2) < TrajectoryEnvelopeScheduler.MINIMUM_SIZE
            ):
                self.logger.debug("Intersection %s with %s too small - skipping", var1, var2)
                return to_return

        var1.refinable = False
        new_trajectories: list[Trajectory] = []
        new_trajectory_envelopes: list[TrajectoryEnvelope] = []

        if not skip_sec1:
            new_trajectories.append(
                Trajectory(list(var1sec1), var1.trajectory.get_dts(0, len(var1sec1)))
            )
            new_trajectories.append(
                Trajectory(
                    list(var1sec2),
                    var1.trajectory.get_dts(len(var1sec1), len(var1sec1) + len(var1sec2)),
                )
            )
            if not skip_sec3:
                new_trajectories.append(
                    Trajectory(
                        list(var1sec3),
                        var1.trajectory.get_dts(
                            len(var1sec1) + len(var1sec2), len(var1.trajectory.pose_steering)
                        ),
                    )
                )
        else:
            new_trajectories.append(
                Trajectory(list(var1sec2), var1.trajectory.get_dts(0, len(var1sec2)))
            )
            if not skip_sec3:
                new_trajectories.append(
                    Trajectory(
                        list(var1sec3),
                        var1.trajectory.get_dts(len(var1sec2), len(var1.trajectory.pose_steering)),
                    )
                )

        new_vars = solver.create_variables(len(new_trajectories))
        assert new_vars is not None
        for i, new_var in enumerate(new_vars):
            te = cast(TrajectoryEnvelope, new_var)
            te.component = var1.component
            te.symbolic_variable_activity.set_symbolic_domain(*var1.symbols)
            assert var1.footprint is not None
            te.set_footprint(var1.footprint)
            # Only for second!
            if (not skip_sec1 and i == 1) or (skip_sec1 and i == 0):
                te.refinable = False
                self.refined_with[var2].append(te)
            te.trajectory = new_trajectories[i]
            te.super_envelope = var1
            te.robot_id = var1.robot_id
            var1.add_sub_envelope(te)
            var1.add_dependent_variables(te)
            new_trajectory_envelopes.append(te)

        starts = AllenIntervalConstraint(Type.Starts)
        starts.from_ = new_trajectory_envelopes[0]
        starts.to = var1
        to_return.add_constraint(starts)

        finishes = AllenIntervalConstraint(Type.Finishes)
        finishes.from_ = new_trajectory_envelopes[-1]
        finishes.to = var1
        to_return.add_constraint(finishes)

        if not skip_sec1:
            min_ttt12 = var1.trajectory.dts[len(var1sec1)]
        else:
            min_ttt12 = var1.trajectory.dts[len(var1sec2)]
        min_time_to_transition12 = int(TrajectoryEnvelope.RESOLUTION * min_ttt12)
        before1 = AllenIntervalConstraint(
            Type.Before, Bounds(min_time_to_transition12, min_time_to_transition12)
        )
        before1.from_ = new_trajectory_envelopes[0]
        before1.to = new_trajectory_envelopes[1]
        to_return.add_constraint(before1)

        if len(new_trajectory_envelopes) > 2:
            min_ttt23 = var1.trajectory.dts[len(var1sec1) + len(var1sec2)]
            min_time_to_transition23 = int(TrajectoryEnvelope.RESOLUTION * min_ttt23)
            before2 = AllenIntervalConstraint(
                Type.Before, Bounds(min_time_to_transition23, min_time_to_transition23)
            )
            before2.from_ = new_trajectory_envelopes[1]
            before2.to = new_trajectory_envelopes[2]
            to_return.add_constraint(before2)

        if not solver.add_constraints(*to_return.get_constraints()):
            raise RuntimeError("Failed to add temporal constraints in refinement!")

        return to_return
