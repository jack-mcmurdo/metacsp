"""Port of multi/spatioTemporal/paths/Trajectory.java."""

from __future__ import annotations

import math
from typing import Sequence, Union

from metacsp.multi.spatio_temporal.paths.pose import Coordinate2D, Coordinate3D, Pose
from metacsp.multi.spatio_temporal.paths.pose_steering import PoseSteering

__all__ = ["Trajectory"]

Coordinate = Union[Coordinate2D, Coordinate3D]


def _coordinate_distance(a: Coordinate, b: Coordinate) -> float:
    """2D Euclidean distance, matching JTS ``Coordinate.distance()``."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


class Trajectory:
    """A path (sequence of :class:`PoseSteering`\\ s) plus a temporal
    profile: fixed durations between successive path points.

    Mirrors Trajectory's six Java constructors -- ``Trajectory(Pose[])``,
    ``Trajectory(PoseSteering[])``, ``Trajectory(Pose[], double[])``,
    ``Trajectory(PoseSteering[], double[])``, ``Trajectory(String
    fileName)``, and ``Trajectory(String... fileNames)`` -- collapsed into
    one Python constructor dispatching on argument count/type, since Python
    has no method overloading.
    """

    _MAX_SPEED: float = 3.0
    _MAX_ACCELERATION: float = 0.3

    def __init__(self, *args: object) -> None:
        if len(args) >= 1 and all(isinstance(a, str) for a in args):
            # Trajectory(String fileName) / Trajectory(String... fileNames)
            combined: list[PoseSteering] = []
            for i, file_name in enumerate(args):
                one_path = self._read_path(file_name)  # type: ignore[arg-type]
                if i == 0:
                    combined.append(one_path[0])
                combined.extend(one_path[1:])
            self._psa = combined
            self._dts = [0.0] * len(self._psa)
            self._update_dts()
        elif len(args) == 1:
            self._psa = self._to_pose_steering_list(args[0])  # type: ignore[arg-type]
            self._dts = [0.0] * len(self._psa)
            self._update_dts()
        elif len(args) == 2:
            seq, dts = args
            self._psa = self._to_pose_steering_list(seq)  # type: ignore[arg-type]
            self._dts = list(dts)  # type: ignore[arg-type]
        else:
            raise TypeError(
                "Trajectory() takes (Pose[]), (PoseSteering[]), (Pose[], dts), "
                "(PoseSteering[], dts), or one-or-more file name strings"
            )
        self._sequence_number_start = 0
        self._sequence_number_end = len(self._psa) - 1

    @staticmethod
    def _to_pose_steering_list(seq: Sequence[object]) -> list[PoseSteering]:
        seq = list(seq)
        if seq and isinstance(seq[0], PoseSteering):
            return list(seq)  # type: ignore[arg-type]
        return [PoseSteering(p, 0.0) for p in seq]  # type: ignore[arg-type]

    def update_sequence_numbers(self, start: int, end: int) -> None:
        """Update the sequence numbers of this trajectory (used when this is
        a trajectory of a sub-trajectory envelope)."""
        self._sequence_number_start = start
        self._sequence_number_end = end

    @property
    def sequence_number_start(self) -> int:
        return self._sequence_number_start

    @property
    def sequence_number_end(self) -> int:
        return self._sequence_number_end

    @property
    def path_length(self) -> float:
        """The length in meters of this Trajectory's path (sum of distances
        between path poses)."""
        length = 0.0
        ps = self.pose_steering
        for i in range(len(ps) - 1):
            length += ps[i].pose.distance_to(ps[i + 1].pose)
        return length

    @property
    def dts(self) -> list[float]:
        return self._dts

    @dts.setter
    def dts(self, dts: Sequence[float]) -> None:
        """Set the minimum transition times between path poses (the fastest
        time profile of this Trajectory). Values are assumed to be in
        seconds."""
        self._dts = list(dts)

    def get_dts(self, from_: int, to: int) -> list[float]:
        """The temporal profile of a portion of this Trajectory."""
        return list(self._dts[from_:to])

    def _get_constant_acceleration(self, percent_complete: float) -> float:
        if percent_complete <= 0.25:
            return Trajectory._MAX_ACCELERATION
        if percent_complete <= 0.78:
            return 0.0
        return -Trajectory._MAX_ACCELERATION

    def _get_acceleration(self, percent_complete: float) -> float:
        return self._get_constant_acceleration(percent_complete)

    def get_sequence_number(self, coord: Coordinate) -> int:
        """The sequence number of the path point closest to a given
        coordinate."""
        min_index = 0
        min_dist = float("inf")
        for i, pos in enumerate(self.positions):
            d = _coordinate_distance(pos, coord)
            if d < min_dist:
                min_dist = d
                min_index = i
        return min_index

    def get_time_left_estimate_from_position(self, position_now: Coordinate) -> float:
        """An estimate of the time left to move on this Trajectory given the
        current position (based on the temporal profile).

        Java overloads this as ``getTimeLeftEstimate(Coordinate)``; renamed
        here (Python has no method overloading) to avoid clashing with
        :meth:`get_time_left_estimate`.
        """
        min_index = 0
        min_dist = float("inf")
        for i, pos in enumerate(self.positions):
            d = _coordinate_distance(pos, position_now)
            if d < min_dist:
                min_dist = d
                min_index = i
        return self.get_time_left_estimate(min_index)

    def get_time_to_estimate(self, sequence_num_now: int, sequence_num_to: int) -> float:
        """An estimate of the time left to move on this Trajectory between
        two path indices (based on the temporal profile)."""
        time_counter = 0.0
        i = sequence_num_now - self._sequence_number_start
        while i <= sequence_num_to:
            time_counter += self._dts[i]
            i += 1
        return time_counter

    def get_time_left_estimate(self, sequence_num: int) -> float:
        """An estimate of the time left to move on this Trajectory given the
        current path index (based on the temporal profile)."""
        time_counter = 0.0
        for i in range(sequence_num - self._sequence_number_start, len(self.dts)):
            time_counter += self.dts[i]
        return time_counter

    def _update_dts(self) -> None:
        dt = 0.1
        u = [0.0]
        s = [0.0]
        positions = self.positions
        tot_distance = 0.0
        for i in range(1, len(self._dts)):
            tot_distance += _coordinate_distance(positions[i - 1], positions[i])
        while s[-1] < tot_distance:
            percent_complete = 0.01
            new_percent = s[-1] / tot_distance
            if new_percent > percent_complete:
                percent_complete = new_percent
            u.append(u[-1] + self._get_acceleration(percent_complete) * dt)
            s.append(s[-1] + u[-1] * dt)
        tot_distance = 0.0
        if self._dts:
            self._dts[0] = 0.0
        prev_sum = 0.0
        for i in range(1, len(self._dts)):
            tot_distance += _coordinate_distance(positions[i - 1], positions[i])
            count_dts = 0
            for j in range(len(s)):
                if s[j] > tot_distance:
                    count_dts = j - 1
                    break
            prev_sum += self._dts[i - 1]
            self._dts[i] = max(count_dts * dt - prev_sum, 0.001)

    @property
    def pose_steering(self) -> list[PoseSteering]:
        """The path (list of PoseSteerings) of this Trajectory."""
        return self._psa

    @property
    def pose(self) -> list[Pose]:
        """The path (list of Poses) of this Trajectory."""
        return [ps.pose for ps in self._psa]

    @property
    def positions(self) -> list[Coordinate]:
        """The list of positions in this Trajectory's path."""
        return [ps.pose.position for ps in self._psa]

    def _read_path(self, file_name: str) -> list[PoseSteering]:
        """Read a ``.path`` file: one pose per line, whitespace-separated,
        with 7 (x y z roll pitch yaw steering), 6 (x y z roll pitch yaw, no
        steering), 4 (x y theta steering), or any-other-length-as-3 (x y
        theta) columns.

        Java catches ``FileNotFoundException`` and silently returns an empty
        path; a missing/unreadable file is instead let to raise here
        (a clearer failure than silently building an empty Trajectory).
        """
        ret: list[PoseSteering] = []
        with open(file_name) as in_file:
            for raw_line in in_file:
                line = raw_line.strip()
                if len(line) == 0:
                    continue
                oneline = line.split(" ")
                ps: PoseSteering
                if len(oneline) == 7:
                    # x, y, z, roll, pitch, yaw, steering
                    ps = PoseSteering(*(float(v) for v in oneline))
                elif len(oneline) == 6:
                    # x, y, z, roll, pitch, yaw
                    ps = PoseSteering(*(float(v) for v in oneline), 0.0)
                elif len(oneline) == 4:
                    # x, y, theta, steering
                    ps = PoseSteering(*(float(v) for v in oneline))
                else:
                    # x, y, theta
                    ps = PoseSteering(float(oneline[0]), float(oneline[1]), float(oneline[2]), 0.0)
                ret.append(ps)
        return ret
