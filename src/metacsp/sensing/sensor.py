"""Port of sensing/Sensor.java."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from metacsp.dispatching.dispatcher import _solver_lock
from metacsp.exceptions import NetworkMaintenanceError
from metacsp.meta.simple_planner.simple_domain import SimpleDomain
from metacsp.multi.activity.activity import Activity
from metacsp.multi.activity.symbolic_variable_activity import SymbolicVariableActivity
from metacsp.multi.allen_interval.allen_interval_constraint import AllenIntervalConstraint
from metacsp.time.bounds import Bounds
from metacsp.utility.logging import get_logger

if TYPE_CHECKING:
    from metacsp.sensing.constraint_network_animator import ConstraintNetworkAnimator

__all__ = ["Sensor"]


class Sensor:
    """A named external sensor whose readings are modeled as a sequence of
    JUSTIFIED activities on this sensor's ``name``-labelled component in a
    :class:`~metacsp.sensing.constraint_network_animator
    .ConstraintNetworkAnimator`'s activity network, each ``Meets``-linked to
    the animator's "Future" activity while the reading holds.
    """

    def __init__(self, name: str, animator: ConstraintNetworkAnimator) -> None:
        self.animator = animator
        self.ans = animator.activity_network_solver
        self.cn = animator.constraint_network
        self.name = name
        self._current_act: Activity | None = None
        self._current_meets_future: AllenIntervalConstraint | None = None
        self._future: SymbolicVariableActivity | None = None
        for time_act in self.cn.get_variables("Time"):
            act = cast(SymbolicVariableActivity, time_act)
            if act.symbolic_variable.symbols[0] == "Future":
                self._future = act
        self.logger = get_logger(type(self))

    def model_sensor_value(self, value: str, time_now: int) -> None:
        """Model a new reading of ``value`` observed at ``time_now``.

        If it differs from the current activity's value, the current
        activity is deadlined and a new activity is started; an unchanged
        reading is ignored.
        """
        with _solver_lock(self.ans):
            make_new = False
            if self._current_act is None:
                make_new = True
            else:
                if self._has_changed(value):
                    deadline = AllenIntervalConstraint(
                        AllenIntervalConstraint.Type.Deadline, Bounds(time_now, time_now)
                    )
                    deadline.from_ = self._current_act.variable
                    deadline.to = self._current_act.variable
                    self.ans.remove_constraint(self._current_meets_future)
                    ret = self.ans.add_constraint(deadline)
                    if not ret:
                        raise NetworkMaintenanceError(deadline)
                    make_new = True

            # First reading or value changed --> make new activity
            if make_new:
                act = self._create_new_activity(value)
                rel = AllenIntervalConstraint(
                    AllenIntervalConstraint.Type.Release, Bounds(time_now, time_now)
                )
                rel.from_ = act.variable
                rel.to = act.variable
                meets_future = AllenIntervalConstraint(AllenIntervalConstraint.Type.Meets)
                meets_future.from_ = act.variable
                meets_future.to = self._future
                self._current_act = act
                self._current_meets_future = meets_future
                ret = self.ans.add_constraints(rel, meets_future)
                if not ret:
                    assert self._future is not None
                    raise NetworkMaintenanceError(self._future.temporal_variable.est, time_now)
                self.logger.info("%s", self._current_act)

    @staticmethod
    def _parse_name(everything: str) -> str:
        ret = everything[everything.index("Sensor") + 6 :]
        ret = ret[: ret.index(")")].strip()
        return ret

    @staticmethod
    def _parse_sensor_value(everything: str, delta: int) -> dict[int, str]:
        ret: dict[int, str] = {}
        last_sv = everything.rfind("SensorValue")
        while last_sv != -1:
            bw = last_sv
            while True:
                bw -= 1
                if everything[bw] == "(":
                    break
            fw = last_sv
            parcounter = 1
            while parcounter != 0:
                ch = everything[fw]
                if ch == "(":
                    parcounter += 1
                elif ch == ")":
                    parcounter -= 1
                fw += 1
            element = everything[bw:fw]
            value = element[element.index("SensorValue") + 11 :].strip()
            tm = int(value[value.index(" ") : value.rindex(")")].strip())
            tm += delta
            value = value[: value.index(" ")].strip()
            ret[tm] = value
            everything = everything[:bw]
            last_sv = everything.rfind("SensorValue")
        return ret

    def post_sensor_value(self, sensor_value: str, time: int) -> int:
        """Queue a reading for the animator to apply at the given time; returns a tracking id."""
        self.animator.post_sensor_value_to_dispatch(self, time, sensor_value)
        return self.get_hash_code(self.name, sensor_value, time)

    @staticmethod
    def get_hash_code(sensor_name: str, sensor_value: str, time: int) -> int:
        """A stable id for a (sensor name, value, time) reading."""
        return _java_string_hash_code(sensor_name + sensor_value + str(time))

    def register_sensor_trace(self, sensor_trace_file: str, delta: int = 0) -> None:
        """Load a ``.st`` sensor-trace file for this sensor and queue its readings,
        shifting all times by ``delta``."""
        try:
            with open(sensor_trace_file) as f:
                kept_lines = [line.rstrip("\n") for line in f if not line.startswith("#")]
            everything = "\n".join(kept_lines) + "\n"
            name = self._parse_name(everything)
            if name == self.name:
                sensor_values = self._parse_sensor_value(everything, delta)
                self.animator.register_sensor_values_to_dispatch(self, sensor_values)
        except OSError:
            self.logger.exception("Failed to read sensor trace %s", sensor_trace_file)

    def _has_changed(self, value: str) -> bool:
        assert self._current_act is not None
        return (
            cast(SymbolicVariableActivity, self._current_act.variable).symbolic_variable.symbols[0]
            != value
        )

    def _create_new_activity(self, value: str) -> SymbolicVariableActivity:
        act = cast(SymbolicVariableActivity, self.ans.create_variable(self.name))
        act.set_symbolic_domain(value)
        act.marking = SimpleDomain.markings.JUSTIFIED
        return act


def _java_string_hash_code(s: str) -> int:
    """Java's ``String.hashCode()``: ``s[0]*31^(n-1) + ... + s[n-1]``, as a
    32-bit signed int."""
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return h
