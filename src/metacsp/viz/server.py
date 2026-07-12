"""Browser-based live viewer server (M-webviz): replaces the dearpygui
``VizApp``/``TimelineWindow`` pair with a websocket server that pushes wire
protocol v2 (documented in ``docs/VIZ.md``) to a static Vite/React frontend
shipped inside the wheel at ``metacsp/viz/static/``.

Timelines are computed on the solver's own thread inside the D2
change-listener callback (:meth:`VizServer._on_change`), not on the asyncio
event loop thread: change listeners fire synchronously right after a
mutation is applied and before another mutation can start on that same
thread, so this sidesteps the torn-read risk of reading the constraint
network concurrently with a solver mutating it. Only the resulting plain
dicts cross the thread boundary (via ``loop.call_soon_threadsafe`` into an
``asyncio.Queue``).
"""

from __future__ import annotations

import asyncio
import importlib.resources
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

import uvicorn
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from metacsp.serialization import (
    constraint_to_dict,
    network_to_dict,
    timeline_to_dict,
    trajectory_envelope_to_dict,
    variable_to_dict,
)

if TYPE_CHECKING:
    from metacsp.framework.constraint_network_change_event import ConstraintNetworkChangeEvent
    from metacsp.multi.spatio_temporal.paths.trajectory_envelope import TrajectoryEnvelope

__all__ = ["VizServer", "serve"]

_DEBOUNCE_SECONDS = 0.05


def _now_ms() -> int:
    return int(time.time() * 1000)


def _static_dir() -> Path | None:
    """The frontend build directory, if one has been built into the
    installed package (see the ``npm --prefix frontend run build`` step in
    ``.github/workflows/release.yml``)."""
    files = importlib.resources.files("metacsp.viz") / "static"
    path = Path(str(files))
    return path if (path / "index.html").is_file() else None


_STATIC_MISSING_MESSAGE = (
    "metacsp/viz/static/ is missing an index.html (this looks like a source "
    "checkout without a frontend build). Build it with:\n"
    "    npm --prefix frontend run build"
)


class VizServer:
    """Owns one Starlette app serving the built frontend plus a ``/ws``
    websocket endpoint that streams wire protocol v2 messages: a full
    ``snapshot`` on connect and every ``period_ms``, an immediate ``delta``
    per D2 change event, and a ``timelines`` message debounced ~50 ms after
    a burst of changes.
    """

    def __init__(
        self,
        solver: Any,
        components: list[str],
        *,
        envelopes: list[TrajectoryEnvelope] | None = None,
        period_ms: int = 2000,
        host: str = "127.0.0.1",
        port: int = 8722,
    ) -> None:
        self.solver = solver
        self.constraint_network = solver.constraint_network
        self.components = list(components)
        self.envelopes = list(envelopes) if envelopes is not None else []
        self.period_ms = period_ms
        self.host = host
        self.port = port

        self._seq = 0
        self._seq_lock = threading.Lock()
        self._clients: set[WebSocket] = set()

        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[dict[str, Any]] | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._snapshot_task: asyncio.Task[None] | None = None
        self._debounce_task: asyncio.Task[None] | None = None
        self._pending_timelines: list[dict[str, Any]] | None = None

        self._uvicorn_server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None

        self.app = self._build_app()
        self.constraint_network.add_change_listener(self._on_change)

    # --- app construction ---

    def _build_app(self) -> Starlette:
        app = Starlette(
            routes=[WebSocketRoute("/ws", self._ws_endpoint)],
            lifespan=self._lifespan,
        )
        static_dir = _static_dir()
        if static_dir is not None:
            app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        return app

    @asynccontextmanager
    async def _lifespan(self, app: Starlette) -> AsyncIterator[None]:
        await self._on_startup()
        try:
            yield
        finally:
            await self._on_shutdown()

    async def _on_startup(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._consumer_task = self._loop.create_task(self._consumer())
        self._snapshot_task = self._loop.create_task(self._snapshot_loop())

    async def _on_shutdown(self) -> None:
        for task in (self._consumer_task, self._snapshot_task, self._debounce_task):
            if task is not None:
                task.cancel()

    def _next_seq(self) -> int:
        with self._seq_lock:
            self._seq += 1
            return self._seq

    # --- websocket ---

    async def _ws_endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        try:
            await websocket.send_json(self._build_snapshot())
            while True:
                await websocket.receive_text()  # inbound "command" is reserved, unimplemented
        except WebSocketDisconnect:
            pass
        finally:
            self._clients.discard(websocket)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        for client in list(self._clients):
            try:
                await client.send_json(message)
            except Exception:
                self._clients.discard(client)

    # --- change-event -> queue bridge ---

    def _on_change(self, event: ConstraintNetworkChangeEvent) -> None:
        """Runs on the solver's own thread. Computes both the delta payload
        and the current timelines here (see module docstring), then hands
        plain dicts across the thread boundary."""
        message: dict[str, Any] = {"kind": "delta", "event": event.kind}
        if event.kind.startswith("variable"):
            message["variable"] = {
                **variable_to_dict(event.payload),
                "component": event.payload.component,
            }
        else:
            message["constraint"] = constraint_to_dict(event.payload)
        timelines = [timeline_to_dict(self.constraint_network, c) for c in self.components]
        if self._loop is not None and self._queue is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, (message, timelines))

    async def _consumer(self) -> None:
        assert self._queue is not None
        while True:
            message, timelines = await self._queue.get()
            message["seq"] = self._next_seq()
            message["ts"] = _now_ms()
            await self._broadcast(message)
            self._schedule_timelines(timelines)

    def _schedule_timelines(self, timelines: list[dict[str, Any]]) -> None:
        assert self._loop is not None
        self._pending_timelines = timelines
        if self._debounce_task is not None:
            self._debounce_task.cancel()
        self._debounce_task = self._loop.create_task(self._debounce_send())

    async def _debounce_send(self) -> None:
        await asyncio.sleep(_DEBOUNCE_SECONDS)
        await self._broadcast(
            {
                "kind": "timelines",
                "seq": self._next_seq(),
                "ts": _now_ms(),
                "timelines": self._pending_timelines,
            }
        )

    # --- periodic snapshot ---

    async def _snapshot_loop(self) -> None:
        while True:
            await asyncio.sleep(self.period_ms / 1000)
            await self._broadcast(self._build_snapshot())

    def _variables_with_component(self) -> list[dict[str, Any]]:
        """``variable_to_dict`` plus a ``"component"`` field: needed by the
        frontend's click-to-inspect panel to find the variables belonging
        to the component an interval came from. Added here rather than in
        ``variable_to_dict`` itself, which stays untouched (see module
        docstring and ``docs/VIZ.md``)."""
        return [
            {**variable_to_dict(v), "component": v.component}
            for v in self.constraint_network.get_variables()
        ]

    def _build_snapshot(self) -> dict[str, Any]:
        return {
            "kind": "snapshot",
            "seq": self._next_seq(),
            "ts": _now_ms(),
            "variables": self._variables_with_component(),
            "constraints": network_to_dict(self.constraint_network)["constraints"],
            "timelines": [timeline_to_dict(self.constraint_network, c) for c in self.components],
            "envelopes": [trajectory_envelope_to_dict(e) for e in self.envelopes],
        }

    # --- lifecycle ---

    def start(self) -> None:
        """Start uvicorn in a daemon thread and return once it is accepting
        connections."""
        if _static_dir() is None:
            raise RuntimeError(_STATIC_MISSING_MESSAGE)
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        self._uvicorn_server = uvicorn.Server(config)
        self._server_thread = threading.Thread(target=self._uvicorn_server.run, daemon=True)
        self._server_thread.start()
        deadline = time.monotonic() + 5.0
        while not self._uvicorn_server.started and time.monotonic() < deadline:
            time.sleep(0.01)

    def run(self) -> None:
        """Block, serving requests, until interrupted."""
        if _static_dir() is None:
            raise RuntimeError(_STATIC_MISSING_MESSAGE)
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        self._uvicorn_server = uvicorn.Server(config)
        self._uvicorn_server.run()

    def stop(self) -> None:
        """Tear down the change listener and shut down uvicorn, if running."""
        self.constraint_network.remove_change_listener(self._on_change)
        if self._uvicorn_server is not None:
            self._uvicorn_server.should_exit = True
        if self._server_thread is not None:
            self._server_thread.join(timeout=5.0)


def serve(
    solver: Any,
    components: list[str],
    *,
    envelopes: list[TrajectoryEnvelope] | None = None,
    period_ms: int = 2000,
    host: str = "127.0.0.1",
    port: int = 8722,
    open_browser: bool = True,
) -> VizServer:
    """Construct a :class:`VizServer`, start it, and (by default) open it in
    the system browser."""
    server = VizServer(
        solver, components, envelopes=envelopes, period_ms=period_ms, host=host, port=port
    )
    server.start()
    if open_browser:
        webbrowser.open(f"http://{host}:{port}/")
    return server
