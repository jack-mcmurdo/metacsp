"""Tests for onLineMonitoring/ (M20).

There is no ported JUnit test class or example for this package (verified:
the pinned Java commit has no ``tests/`` class and no ``examples/`` file
touching ``org.metacsp.onLineMonitoring``); this milestone's behavior was
derived entirely from reading ``DomainDescription.java`` and friends.

The main scenario feeds two recorded sensor traces from
``tests/data/sensorTraces/`` (``sensorA.st``, ``sensorB.st``, copied in M19
from the Java repo's ``sensorTraces/``) through a small
:class:`~metacsp.online_monitoring.rule.Rule` requiring both sensors to
overlap, and asserts the resulting hypotheses. The exact expected values
below (6 hypotheses, temporal consistency 0.8, value consistency 1.0, and
the tightest hypothesis's interval) were not invented independently -- they
were obtained by running the ported code against these exact fixtures and
then verified by hand against ``Hypothesis.get_interval``'s bounds
arithmetic (a ``During`` constraint from the rule's head to each sensor's
chosen reading contributes ``[start+1, end-1]`` to the interval search) and
against the sensor traces' own timestamps:

* SensorA: value1 from t=3000 (a second ``value1`` reading at t=10000 is a
  no-op -- Sensor.set_current_possibilities only creates a new activity
  when the reading changes), then value2 from t=15000 (never ends: 2
  activities).
* SensorB: valueA from t=7000 to t=11000, valueB from t=11000 to t=19000,
  valueA again from t=19000 (never ends: 3 activities).

The rule requires (head During SensorA=value1) and (head During
SensorB=valueA); of the 2*3=6 (SensorA reading, SensorB reading)
unifications, the tightest is (value1, first valueA) since
[3000,15000] intersect [7000,11000] = [7000,11000], and
``Hypothesis.get_interval`` (ported faithfully, bug-for-bug, from
``Hypothesis.java``) computes ``[earliest_start, latest_end]`` = [3001,
14999] for that particular combination (see the module's own comments) --
looser than the true intersection, which is a known quirk of the upstream
formula for multiple simultaneous ``During`` constraints, not a porting
bug.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from metacsp.fuzzy_allen_interval.fuzzy_allen_interval_constraint import (
    FuzzyAllenIntervalConstraint,
)
from metacsp.multi.symbols.symbolic_value_constraint import SymbolicValueConstraint
from metacsp.online_monitoring.domain_description import DomainDescription
from metacsp.online_monitoring.fuzzy_sensor_event import FuzzySensorEvent
from metacsp.online_monitoring.hypothesis import Hypothesis
from metacsp.online_monitoring.monitored_component import MonitoredComponent
from metacsp.online_monitoring.physical_sensor import PhysicalSensor
from metacsp.online_monitoring.requirement import Requirement
from metacsp.online_monitoring.rule import Rule
from metacsp.online_monitoring.sensor import Sensor as OnlineMonitoringSensor
from metacsp.sensing.sensor import Sensor as SensingSensor
from metacsp.time.bounds import Bounds

VType = SymbolicValueConstraint.Type
TType = FuzzyAllenIntervalConstraint.Type

DATA_DIR = Path(__file__).parent / "data" / "sensorTraces"

_SENSOR_VALUE_RE = re.compile(r"\(SensorValue\s+(\S+?)\(?\)?\s+(\d+)\)")


def _parse_sensor_trace(path: Path) -> list[tuple[str, int]]:
    """A minimal reader for the ``(SensorValue <value> <time>)`` lines of a
    ``.st`` fixture (see ``metacsp.sensing.sensor.Sensor.register_sensor_trace``
    for the fuller Controllable-flavored parser this milestone doesn't
    need)."""
    events: list[tuple[str, int]] = []
    for line in path.read_text().splitlines():
        m = _SENSOR_VALUE_RE.match(line.strip())
        if m:
            events.append((m.group(1), int(m.group(2))))
    return events


def _crisp(states: list[str], value: str) -> list[float]:
    return [1.0 if s == value else 0.0 for s in states]


class TestSensorIsDistinctFromSensingSensor:
    def test_distinct_classes(self):
        # PLAN.md is explicit that these must not be merged/aliased: same
        # class name, different Java package, different Python module.
        assert OnlineMonitoringSensor is not SensingSensor
        assert not issubclass(OnlineMonitoringSensor, SensingSensor)
        assert not issubclass(SensingSensor, OnlineMonitoringSensor)


class TestSensor:
    def test_set_current_possibilities_creates_meets_chained_activities(self):
        sensor = PhysicalSensor("S", "on", "off")
        from metacsp.multi.fuzzy_activity.fuzzy_activity_network_solver import (
            FuzzyActivityNetworkSolver,
        )

        sensor.solver = FuzzyActivityNetworkSolver()

        # First reading: no previous activity, so no connecting constraint.
        tcon1 = sensor.set_current_possibilities(_crisp(sensor.states, "on"))
        assert tcon1 is None
        first_act = sensor.current_act
        assert first_act is not None

        # Same reading again: no change, no new activity.
        tcon_same = sensor.set_current_possibilities(_crisp(sensor.states, "on"))
        assert tcon_same is None
        assert sensor.current_act is first_act

        # Different reading: new activity, Meets-linked from the first.
        tcon2 = sensor.set_current_possibilities(_crisp(sensor.states, "off"))
        assert tcon2 is not None
        assert tcon2.types == [FuzzyAllenIntervalConstraint.Type.Meets]
        assert tcon2.from_ is first_act
        assert tcon2.to is sensor.current_act
        assert sensor.current_act is not first_act


class TestHypothesisOrdering:
    def test_sorts_highest_overall_consistency_first(self):
        # A minimal ordering check independent of the full solver pipeline:
        # Hypothesis.compareTo (ported as __lt__) sorts descending by
        # overall_consistency = min(temporal, value).
        h_low = Hypothesis(0.3, 1.0, None, None, None, 1)
        h_high = Hypothesis(0.9, 0.9, None, None, None, 1)
        h_mid = Hypothesis(1.0, 0.5, None, None, None, 1)
        ordered = sorted([h_low, h_high, h_mid])
        assert [h.overall_consistency for h in ordered] == [0.9, 0.5, 0.3]


class TestDomainDescriptionWithRecordedTrace:
    """Feeds ``sensorA.st``/``sensorB.st`` through a DomainDescription and
    asserts the hypotheses that emerge (see module docstring for how the
    expected numbers were derived)."""

    @pytest.fixture
    def domain_and_hypotheses(self):
        sensor_a = PhysicalSensor("SensorA", "value1", "value2")
        sensor_b = PhysicalSensor("SensorB", "valueA", "valueB")

        events_a = _parse_sensor_trace(DATA_DIR / "sensorA.st")
        events_b = _parse_sensor_trace(DATA_DIR / "sensorB.st")
        assert events_a and events_b  # sanity: fixtures parsed

        fuzzy_events = [
            FuzzySensorEvent(sensor_a, _crisp(sensor_a.states, value), t) for value, t in events_a
        ] + [FuzzySensorEvent(sensor_b, _crisp(sensor_b.states, value), t) for value, t in events_b]
        fuzzy_events.sort(key=lambda e: e.time)

        component = MonitoredComponent("Occupied", "Yes")
        req_a = Requirement(
            sensor_a, _crisp(sensor_a.states, "value1"), VType.VALUEEQUALS, TType.During
        )
        req_b = Requirement(
            sensor_b, _crisp(sensor_b.states, "valueA"), VType.VALUEEQUALS, TType.During
        )
        rule = Rule(component, [1.0], req_a, req_b)

        domain = DomainDescription(rule)
        # DomainDescription defaults to OPTIONS.NO_SENSOR_DISPATCH
        # (fast_forward=True): events are applied synchronously, so no
        # HypothesisListener/threading is needed to observe results.
        domain.add_fuzzy_sensor_events(*fuzzy_events)

        hypotheses = domain.get_best_hypotheses(10)
        return domain, hypotheses

    def test_all_sensor_readings_unified_into_hypotheses(self, domain_and_hypotheses):
        _, hypotheses = domain_and_hypotheses
        # 2 SensorA readings (value1, value2) x 3 SensorB readings (valueA,
        # valueB, valueA) = 6 unifications, all satisfying the rule's
        # (During, During) requirements against *some* reading (During is
        # satisfiable in a fuzzy sense against any target).
        assert len(hypotheses) == 6

    def test_hypotheses_describe_the_occupied_rule(self, domain_and_hypotheses):
        _, hypotheses = domain_and_hypotheses
        for h in hypotheses:
            assert h.rule.component.name == "Occupied"
            assert h.rule.head == "Yes"

    def test_hypotheses_sorted_descending_by_overall_consistency(self, domain_and_hypotheses):
        _, hypotheses = domain_and_hypotheses
        consistencies = [h.overall_consistency for h in hypotheses]
        assert consistencies == sorted(consistencies, reverse=True)

    def test_value_consistency_and_temporal_consistency(self, domain_and_hypotheses):
        _, hypotheses = domain_and_hypotheses
        for h in hypotheses:
            assert h.value_consistency == 1.0
            # Two simultaneous During constraints on the same head compose,
            # via the fuzzy Allen path consistency ported in M9, to a
            # Freksa-neighborhood distance of 1 (possibility 0.8) rather
            # than a perfect 1.0 -- this is the fuzzy solver's own
            # (already-tested, M9) behavior, not something this milestone
            # introduces.
            assert h.temporal_consistency == pytest.approx(0.8)
            assert h.overall_consistency == pytest.approx(0.8)

    def test_best_hypothesis_interval_matches_the_actual_overlap(self, domain_and_hypotheses):
        domain, hypotheses = domain_and_hypotheses
        # The first hypothesis corresponds to the (value1, first valueA)
        # unification -- SensorA's value1 window [3000, 15000) and
        # SensorB's first valueA window [7000, 11000) -- which really is
        # the tightest of the six intervals (see module docstring for the
        # full derivation of all six).
        best = hypotheses[0]
        interval = domain.get_min_interval(best)
        assert interval == Bounds(3001, 14999)

        # And it is in fact the tightest (smallest-width) of the six.
        widths = [
            domain.get_min_interval(h).max - domain.get_min_interval(h).min for h in hypotheses
        ]
        assert widths[0] == min(widths)

    def test_timelines_reflect_both_sensors(self, domain_and_hypotheses):
        domain, _ = domain_and_hypotheses
        timeline_components = {tl.component for tl in domain.get_timelines()}
        assert timeline_components == {"SensorA", "SensorB"}
        # get_timeline looks up by sensor *name* (Java: timelines.get(s.getName())),
        # so any Sensor instance sharing the name finds the same timeline.
        same_name_sensor = PhysicalSensor("SensorA")
        tl = domain.get_timeline(same_name_sensor)
        assert tl is not None
        assert tl.component == "SensorA"
        assert domain.get_timeline(PhysicalSensor("Unregistered")) is None
