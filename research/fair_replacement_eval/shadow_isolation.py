"""Time-bounded, process-isolated planner execution for shadow mode (research only).

``SubprocessPlanner`` runs the planner in a separate (spawned) worker process and waits for each
recommendation for at most ``timeout_sec``. If the worker does not answer in time it is
*terminated and reaped* (SIGTERM, then SIGKILL after ``grace_sec``), so no computation keeps running
in the background, and a fresh worker is started lazily for the next call. Waiting alone is never
the only remedy.

Time accounting per call (all in nanoseconds, measured on this machine):

* ``compute_ns``   - time spent inside ``planner.select_action`` in the worker;
* ``roundtrip_ns`` - parent-side time from sending the request until the reply arrived (or until the
  deadline expired); this is what blocks the DQN loop;
* ``ipc_ns``       - ``roundtrip_ns - compute_ns``: pickling, pipe transfer, scheduling and worker
  loop overhead, which cannot be separated further;
* ``startup_ns``   - time to spawn and initialise a worker, when this call had to start one (not part
  of ``roundtrip_ns``);
* ``cleanup_ns``   - time to terminate and reap a worker after a timeout or a crash.

Planner state: the worker owns the planner object, so its internal history (``planner_ops_hist`` uses
the previous observation of the episode) lives in the worker. After a timeout, crash or skipped
step the history is incomplete; the caller marks such recommendations ``history_intact = False``.

Limits (see SHADOW_MODE.md): a planner that spawns its own child processes is not handled; if the
parent is killed with SIGKILL a worker stuck in an endless computation is not reclaimed; CPU/memory
limits are not enforced, only wall-clock time.
"""

from __future__ import annotations

import multiprocessing as mp
import time
from functools import partial
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np

DEFAULT_TIMEOUT_SEC = 1.0
DEFAULT_STARTUP_TIMEOUT_SEC = 60.0
DEFAULT_GRACE_SEC = 1.0
DEFAULT_MAX_CONSECUTIVE_TIMEOUTS = 3


def build_planner(name: str, sigma_grid: list[float]) -> Any:
    """Picklable (module-level) planner factory used in the worker; same-information tiers only."""
    from research.fair_replacement_eval.policies import make_planners

    planner = make_planners(sigma_grid, {})[name]
    if planner.forecast != "persistence":
        raise ValueError("shadow mode rejects planners that read the true future price")
    return planner


def planner_factory_for(name: str, sigma_grid: list[float]) -> Callable[[], Any]:
    return partial(build_planner, name, list(sigma_grid))


def _worker_main(conn: Any, factory: Callable[[], Any]) -> None:
    """Worker loop: build the planner, then answer one request at a time until told to stop."""
    try:
        planner = factory()
    except BaseException as exc:  # noqa: BLE001 - report any startup failure to the parent
        try:
            conn.send(("startup_error", f"{type(exc).__name__}: {exc}"))
        finally:
            conn.close()
        return
    conn.send(("ready",))
    while True:
        try:
            message = conn.recv()
        except (EOFError, OSError):  # parent went away
            return
        if message is None:
            return
        step_index, observation, max_steps, min_safe_fuel = message
        observation = np.asarray(observation, dtype=float)
        observation.setflags(write=False)
        view = SimpleNamespace(max_steps=int(max_steps), min_safe_fuel=float(min_safe_fuel))
        t0 = time.perf_counter_ns()
        try:
            raw = planner.select_action(view, observation, int(step_index))
            compute_ns = time.perf_counter_ns() - t0
            reply: tuple[Any, ...] = ("ok", raw, compute_ns)
        except Exception as exc:  # noqa: BLE001 - a planner exception is a recorded failure, not a crash
            compute_ns = time.perf_counter_ns() - t0
            reply = ("error", f"{type(exc).__name__}: {exc}", compute_ns)
        try:
            conn.send(reply)
        except Exception as exc:  # noqa: BLE001 - e.g. an action that cannot be pickled
            conn.send(("error", f"unsendable planner result ({type(exc).__name__}: {exc})", compute_ns))


class SubprocessPlanner:
    """Run a planner in a worker process with a per-call deadline and guaranteed reclamation."""

    def __init__(
        self,
        factory: Callable[[], Any],
        *,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        startup_timeout_sec: float = DEFAULT_STARTUP_TIMEOUT_SEC,
        grace_sec: float = DEFAULT_GRACE_SEC,
    ) -> None:
        if not timeout_sec > 0 or not startup_timeout_sec > 0 or not grace_sec > 0:
            raise ValueError("timeouts must be positive")
        self.factory = factory
        self.timeout_sec = float(timeout_sec)
        self.startup_timeout_sec = float(startup_timeout_sec)
        self.grace_sec = float(grace_sec)
        self._ctx = mp.get_context("spawn")
        self._proc: Any = None
        self._conn: Any = None
        self.unavailable: str | None = None
        self.stats: dict[str, Any] = {
            "workers_started": 0, "workers_killed_on_timeout": 0, "workers_died": 0,
            "workers_stopped_normally": 0, "workers_not_reaped": 0, "startup_failures": 0,
        }
        self.reaped_pids: list[int] = []

    @property
    def has_worker(self) -> bool:
        return self._proc is not None

    # ------------------------------------------------------------------ lifecycle
    def _start(self) -> tuple[bool, int]:
        t0 = time.perf_counter_ns()
        parent_conn, child_conn = self._ctx.Pipe(duplex=True)
        proc = self._ctx.Process(target=_worker_main, args=(child_conn, self.factory), daemon=True)
        proc.start()
        child_conn.close()  # the parent keeps only its own end
        self._proc, self._conn = proc, parent_conn
        self.stats["workers_started"] += 1
        reason = None
        try:
            if not parent_conn.poll(self.startup_timeout_sec):
                reason = f"planner worker did not become ready within {self.startup_timeout_sec:g}s"
            else:
                message = parent_conn.recv()
                if message[0] == "startup_error":
                    reason = f"planner worker failed to start: {message[1]}"
                elif message[0] != "ready":
                    reason = f"unexpected startup message {message[0]!r}"
        except (EOFError, OSError):
            reason = "planner worker exited during startup"
        if reason is not None:
            self.stats["startup_failures"] += 1
            self.unavailable = reason
            self._reap()
        return reason is None, time.perf_counter_ns() - t0

    def _reap(self) -> int:
        """Terminate (then kill) the worker, join it and release its pipe. Returns elapsed ns."""
        t0 = time.perf_counter_ns()
        proc, conn = self._proc, self._conn
        self._proc = self._conn = None
        if proc is not None:
            pid = proc.pid
            if proc.is_alive():
                proc.terminate()
                proc.join(self.grace_sec)
            if proc.is_alive():
                proc.kill()
                proc.join(self.grace_sec)
            if proc.is_alive():
                self.stats["workers_not_reaped"] += 1
            else:
                proc.join(0)
                try:
                    proc.close()
                except ValueError:
                    pass
                if pid is not None:
                    self.reaped_pids.append(pid)
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass
        return time.perf_counter_ns() - t0

    def close(self) -> None:
        """Stop the worker politely, then make sure it is gone."""
        if self._proc is None:
            return
        try:
            self._conn.send(None)
            self._proc.join(self.grace_sec)
            if not self._proc.is_alive():
                self.stats["workers_stopped_normally"] += 1
        except (OSError, ValueError):
            pass
        self._reap()

    def __enter__(self) -> "SubprocessPlanner":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ calls
    def call(self, step_index: int, observation: Any, max_steps: int, min_safe_fuel: float) -> dict[str, Any]:
        """One recommendation request. Never raises for planner/worker problems.

        Returns ``status`` in {ok, error, timeout}; ``raw`` (ok only); ``error``; and the timing
        fields described in the module docstring (``None`` where not measurable).
        """
        out: dict[str, Any] = {
            "status": "ok", "raw": None, "error": "", "compute_ns": None, "roundtrip_ns": None,
            "ipc_ns": None, "startup_ns": None, "cleanup_ns": None, "worker_restarted": False,
        }
        if self.unavailable is not None:
            return {**out, "status": "error", "error": f"PlannerUnavailable: {self.unavailable}"}
        if self._proc is None:
            started, startup_ns = self._start()
            out["startup_ns"], out["worker_restarted"] = startup_ns, True
            if not started:
                return {**out, "status": "error", "error": f"PlannerUnavailable: {self.unavailable}"}
        payload = (int(step_index), np.array(observation, dtype=float, copy=True), int(max_steps), float(min_safe_fuel))
        t0 = time.perf_counter_ns()
        try:
            self._conn.send(payload)
            answered = self._conn.poll(self.timeout_sec)
            if answered:
                reply = self._conn.recv()
        except (EOFError, OSError, BrokenPipeError):
            out["roundtrip_ns"] = time.perf_counter_ns() - t0
            exitcode = self._proc.exitcode if self._proc is not None else None
            out["cleanup_ns"] = self._reap()
            self.stats["workers_died"] += 1
            return {**out, "status": "error", "error": f"PlannerWorkerDied: worker exited (exitcode={exitcode})"}
        out["roundtrip_ns"] = time.perf_counter_ns() - t0
        if not answered:
            out["cleanup_ns"] = self._reap()
            self.stats["workers_killed_on_timeout"] += 1
            return {**out, "status": "timeout", "error": f"TimeoutError: no answer within {self.timeout_sec:g}s; worker terminated"}
        if reply[0] == "ok":
            out.update(raw=reply[1], compute_ns=int(reply[2]))
        else:
            out.update(status="error", error=str(reply[1]), compute_ns=int(reply[2]))
        out["ipc_ns"] = max(0, out["roundtrip_ns"] - out["compute_ns"])
        return out
