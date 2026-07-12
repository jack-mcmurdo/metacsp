"""JSON snapshot/delta export (M21, D10).

Replaces the byte-image encoding pipeline of
``utility/timelinePlotting/TimelinePublisher.java`` (which renders Swing
``BufferedImage``s of ``SymbolicTimeline``s to PNG) with a plain JSON
description of the constraint network, suitable for the in-scope
``metacsp.viz`` live viewer and for a future browser-based consumer (see
``docs/VIZ.md``). Not a 1:1 port of any single Java class -- D10 explicitly
does not require Swing-UI fidelity.
"""

from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from metacsp.framework.constraint import Constraint
    from metacsp.framework.constraint_network import ConstraintNetwork
    from metacsp.framework.constraint_network_change_event import ConstraintNetworkChangeEvent
    from metacsp.framework.variable import Variable
    from metacsp.multi.activity.activity_network_solver import ActivityNetworkSolver
    from metacsp.multi.spatio_temporal.paths.trajectory_envelope import TrajectoryEnvelope

__all__ = [
    "variable_to_dict",
    "constraint_to_dict",
    "network_to_dict",
    "timeline_to_dict",
    "trajectory_envelope_to_dict",
    "SnapshotPublisher",
]


def variable_to_dict(v: Variable) -> dict[str, Any]:
    """``{"id", "class", "domain": str}`` per PLAN.md's M21 schema."""
    return {"id": v.id, "class": type(v).__name__, "domain": str(v.domain)}


def constraint_to_dict(c: Constraint) -> dict[str, Any]:
    """``{"class", "from", "to", "label": str}``; ``from``/``to`` are variable
    ids, ``None`` for constraints that are not a ``BinaryConstraint``."""
    from_ = getattr(c, "from_", None)
    to = getattr(c, "to", None)
    return {
        "class": type(c).__name__,
        "from": from_.id if from_ is not None else None,
        "to": to.id if to is not None else None,
        "label": str(c),
    }


def network_to_dict(net: ConstraintNetwork) -> dict[str, Any]:
    return {
        "variables": [variable_to_dict(v) for v in net.get_variables()],
        "constraints": [constraint_to_dict(c) for c in net.get_constraints()],
    }


def timeline_to_dict(
    an: ConstraintNetwork | ActivityNetworkSolver, component: str
) -> dict[str, Any]:
    """The ``SymbolicTimeline`` for *component*, flattened to JSON: pulses,
    and the joined symbols holding in ``[pulses[i], pulses[i+1])`` for each
    ``i`` (``None`` for an undetermined/empty interval). ``values`` has the
    same length as ``pulses``, with an always-``None`` trailing entry --
    mirrors ``Timeline.java``'s own values-array padding."""
    from metacsp.meta.symbols_and_time.symbolic_timeline import SymbolicTimeline

    tl = SymbolicTimeline(an, component)
    values: list[list[str] | None] = [None if v is None else list(v.strings) for v in tl.values]
    return {"component": component, "pulses": list(tl.pulses), "values": values}


def trajectory_envelope_to_dict(te: TrajectoryEnvelope) -> dict[str, Any]:
    """GeoJSON-style ``Feature`` for a ``TrajectoryEnvelope``'s spatial
    envelope polygon, with robot/component/temporal metadata as properties."""
    from shapely.geometry import mapping

    geometry = mapping(te.spatial_envelope.polygon)
    return {
        "type": "Feature",
        "geometry": {"type": geometry["type"], "coordinates": geometry["coordinates"]},
        "properties": {
            "id": te.id,
            "component": te.component,
            "robot_id": te.robot_id,
            "symbols": list(te.symbols),
            "est": te.temporal_variable.est,
            "eet": te.temporal_variable.eet,
        },
    }


class SnapshotPublisher:
    """Port of the periodic-publish role of
    ``utility/timelinePlotting/TimelinePublisher.java``, minus Swing image
    encoding: a D9-style daemon thread that calls ``callback(json_str)``
    every ``period_ms`` with a full network snapshot, and once immediately
    on every D2 change event (delta) via
    :meth:`~metacsp.framework.constraint_network.ConstraintNetwork
    .add_change_listener`.

    Each JSON message is an object ``{"kind": "snapshot" | "delta", ...}``:
    a ``"snapshot"`` message additionally has the keys of
    :func:`network_to_dict`; a ``"delta"`` message has ``"event"`` set to
    the fired ``ConstraintNetworkChangeEvent.kind`` and ``"variable"`` (or
    ``"constraint"``) set to the changed item's :func:`variable_to_dict` (or
    :func:`constraint_to_dict`).
    """

    def __init__(self, solver: Any, period_ms: int, callback: Callable[[str], None]) -> None:
        self.solver = solver
        self.constraint_network: ConstraintNetwork = solver.constraint_network
        self.period_ms = period_ms
        self.callback = callback
        self._teardown = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.constraint_network.add_change_listener(self._on_change)

    def start(self) -> None:
        self._thread.start()

    def teardown(self) -> None:
        self._teardown = True
        self.constraint_network.remove_change_listener(self._on_change)

    def _on_change(self, event: ConstraintNetworkChangeEvent) -> None:
        message: dict[str, Any] = {"kind": "delta", "event": event.kind}
        if event.kind.startswith("variable"):
            message["variable"] = variable_to_dict(event.payload)  # type: ignore[arg-type]
        else:
            message["constraint"] = constraint_to_dict(event.payload)  # type: ignore[arg-type]
        self.callback(json.dumps(message))

    def publish(self) -> None:
        """Publish one full snapshot now (also called every tick by the
        background thread)."""
        message = {"kind": "snapshot", **network_to_dict(self.constraint_network)}
        self.callback(json.dumps(message))

    def _run(self) -> None:
        import time

        while not self._teardown:
            self.publish()
            time.sleep(self.period_ms / 1000)
