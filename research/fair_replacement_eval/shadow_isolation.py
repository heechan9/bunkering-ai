"""Time-bounded, process-isolated planner execution for shadow mode (research only).

``SubprocessPlanner`` runs the planner in a separate (spawned) worker process and waits for each
recommendation for at most ``timeout_sec``. If the worker does not answer in time it is terminated
(SIGTERM, then SIGKILL after ``grace_sec``) and joined, so the computation does not keep running in
the background, and a fresh worker is started lazily for the next call. Reclamation is best effort:
if a worker survives SIGKILL plus the join grace, it is counted, its pid is kept, and no further
worker is started in this run.

Reply protocol. The worker never sends planner objects to the parent. It validates and normalises the
planner's return value *inside the worker* and sends a small JSON message (at most
``MAX_MESSAGE_BYTES``): ``["ok", <int action>, compute_ns]``, ``["invalid", <short text>, compute_ns]``
or ``["error", <short text>, compute_ns]``. The parent reads it with ``recv_bytes(maxlength=...)`` and
parses it against a fixed schema; it never unpickles anything that came from the planner side. Any
reply that does not match the schema is a protocol error: the worker is discarded.

Deadline. ``timeout_sec`` bounds the parent-side time from starting to send the request until the
complete reply has been received and parsed (``roundtrip_ns``). The request and the reply are far
smaller than the pipe buffer, so sending never waits for the worker; the reply is a single bounded
message. What the deadline does *not* cover: starting a worker (bounded separately by
``startup_timeout_sec``) and terminating/joining a worker after a timeout or failure (bounded by
at most about ``2 * grace_sec``). Planner code that deliberately writes to the worker's pipe is out of
scope.

Time accounting per call (all in nanoseconds, measured on this machine):

* ``compute_ns``   - time spent inside ``planner.select_action`` in the worker;
* ``roundtrip_ns`` - parent-side send + wait + receive + parse (see Deadline); this is what blocks the
  DQN loop for the call itself;
* ``ipc_ns``       - ``roundtrip_ns - compute_ns``: serialisation, pipe transfer, scheduling and worker
  loop overhead, which cannot be separated further;
* ``startup_ns``   - spawn and handshake time when this call had to start a worker (not part of
  ``roundtrip_ns``); a failed start's cleanup is reported separately in ``cleanup_ns``;
* ``cleanup_ns``   - time to terminate and join a worker after a timeout, a crash or a failed start.

Planner state: the worker owns the planner object, so its internal history (``planner_ops_hist`` uses
the previous observation of the episode) lives in the worker. After a timeout, crash or skipped
step the history is incomplete; the caller marks such recommendations ``history_intact = False``.

Limits (see SHADOW_MODE.md): a planner that spawns its own child processes is not handled; if the
parent is killed with SIGKILL a worker stuck in an endless computation is not reclaimed; CPU/memory
limits are not enforced, only wall-clock time.
"""

from __future__ import annotations

import json
import math
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
MAX_MESSAGE_BYTES = 4096  # hard cap on any worker -> parent message
MAX_TEXT_CHARS = 300
_INT64 = 2**63


def finite_positive(name: str, value: Any) -> float:
    """Validate a duration: a real number (not bool), finite and > 0."""
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be a finite number > 0, got {value!r}")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number > 0, got {value!r}")
    return value


def non_negative_int(name: str, value: Any) -> int:
    """Validate a count: an integer (not bool, not float) >= 0."""
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) < 0:
        raise ValueError(f"{name} must be an integer >= 0, got {value!r}")
    return int(value)


def build_planner(name: str, sigma_grid: list[float]) -> Any:
    """Picklable (module-level) planner factory used in the worker; same-information tiers only."""
    from research.fair_replacement_eval.policies import make_planners

    planner = make_planners(sigma_grid, {})[name]
    if planner.forecast != "persistence":
        raise ValueError("shadow mode rejects planners that read the true future price")
    return planner


def planner_factory_for(name: str, sigma_grid: list[float]) -> Callable[[], Any]:
    return partial(build_planner, name, list(sigma_grid))


# ---------------------------------------------------------------------- worker side


def _text(value: Any) -> str:
    try:
        text = str(value)
    except Exception:  # noqa: BLE001 - an object whose __str__ fails must not break the protocol
        text = f"<unprintable {type(value).__name__}>"
    return text[:MAX_TEXT_CHARS]


def _send(conn: Any, kind: str, value: Any, compute_ns: int | None = None) -> None:
    if isinstance(value, str):
        value = value[:MAX_TEXT_CHARS]
    payload = json.dumps([kind, value, compute_ns], ensure_ascii=True, separators=(",", ":")).encode("ascii")
    conn.send_bytes(payload)  # a few hundred bytes at most: never blocks on the pipe buffer


def normalise_result(raw: Any) -> tuple[str, Any]:
    """Worker side: turn whatever the planner returned into ("ok", int) or ("invalid", short text)."""
    if isinstance(raw, bool) or not isinstance(raw, (int, np.integer)):
        return "invalid", f"non-integer action ({type(raw).__name__})"
    value = int(raw)
    if not -_INT64 <= value < _INT64:
        return "invalid", "action outside the 64-bit integer range"
    return "ok", value


def _worker_main(conn: Any, factory: Callable[[], Any]) -> None:
    """Worker loop: build the planner, then answer one request at a time until told to stop."""
    try:
        planner = factory()
    except BaseException as exc:  # noqa: BLE001 - report any startup failure to the parent
        try:
            _send(conn, "startup_error", f"{type(exc).__name__}: {_text(exc)}")
        finally:
            conn.close()
        return
    _send(conn, "ready", "")
    while True:
        try:
            message = conn.recv()  # request from the parent: tuple of primitives + a float array
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
            kind, value = normalise_result(raw)
        except Exception as exc:  # noqa: BLE001 - a planner exception is a recorded failure, not a crash
            compute_ns = time.perf_counter_ns() - t0
            kind, value = "error", f"{type(exc).__name__}: {_text(exc)}"
        try:
            _send(conn, kind, value, compute_ns)
        except Exception as exc:  # noqa: BLE001 - never let a send problem kill the loop silently
            _send(conn, "error", f"reply could not be sent ({type(exc).__name__})", compute_ns)


# ---------------------------------------------------------------------- parent side


class ProtocolError(Exception):
    """The worker's reply did not match the fixed schema."""


def parse_message(data: bytes) -> tuple[str, Any, int | None]:
    """Parent side: strict schema check of one worker message (never unpickles)."""
    try:
        obj = json.loads(data.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError(f"unparseable reply ({type(exc).__name__})") from None
    if not isinstance(obj, list) or len(obj) != 3:
        raise ProtocolError("reply is not a 3-element list")
    kind, value, compute_ns = obj
    if kind not in ("ready", "startup_error", "ok", "invalid", "error"):
        raise ProtocolError("unknown reply kind")
    if kind == "ok":
        if isinstance(value, bool) or not isinstance(value, int) or not -_INT64 <= value < _INT64:
            raise ProtocolError("ok reply without an integer action")
    elif not isinstance(value, str) or len(value) > MAX_TEXT_CHARS:
        raise ProtocolError("reply text is not a short string")
    if kind in ("ok", "invalid", "error"):
        if isinstance(compute_ns, bool) or not isinstance(compute_ns, int) or compute_ns < 0:
            raise ProtocolError("reply without a valid compute time")
    elif compute_ns is not None:
        raise ProtocolError("unexpected compute time")
    return kind, value, compute_ns


class SubprocessPlanner:
    """Run a planner in a worker process with a per-call deadline and best-effort reclamation."""

    def __init__(
        self,
        factory: Callable[[], Any],
        *,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        startup_timeout_sec: float = DEFAULT_STARTUP_TIMEOUT_SEC,
        grace_sec: float = DEFAULT_GRACE_SEC,
    ) -> None:
        self.factory = factory
        self.timeout_sec = finite_positive("timeout_sec", timeout_sec)
        self.startup_timeout_sec = finite_positive("startup_timeout_sec", startup_timeout_sec)
        self.grace_sec = finite_positive("grace_sec", grace_sec)
        self._ctx = mp.get_context("spawn")
        self._proc: Any = None
        self._conn: Any = None
        self.unavailable: str | None = None
        self.stats: dict[str, Any] = {
            "workers_started": 0, "workers_killed_on_timeout": 0, "workers_died": 0,
            "workers_stopped_normally": 0, "workers_not_reaped": 0, "startup_failures": 0,
            "protocol_errors": 0,
        }
        self.reaped_pids: list[int] = []
        self.unreaped_pids: list[int] = []
        self._unreaped_procs: list[Any] = []

    @property
    def has_worker(self) -> bool:
        return self._proc is not None

    # ------------------------------------------------------------------ lifecycle
    def _fail_unavailable(self, reason: str) -> None:
        self.stats["startup_failures"] += 1
        self.unavailable = reason

    def _start(self) -> tuple[bool, int, int | None]:
        """Spawn a worker and wait for its handshake. Returns (ok, startup_ns, cleanup_ns).

        Every failure on the way (pipe creation, process creation/start, handshake) is recorded as
        "planner unavailable" and any partially created resource is released.
        """
        t0 = time.perf_counter_ns()
        parent_conn = child_conn = proc = None
        reason: str | None = None
        try:
            parent_conn, child_conn = self._ctx.Pipe(duplex=True)
            proc = self._ctx.Process(target=_worker_main, args=(child_conn, self.factory), daemon=True)
            proc.start()
            self.stats["workers_started"] += 1
        except Exception as exc:  # noqa: BLE001 - OS-level failures (fd/process limits, spawn errors)
            reason = f"planner worker could not be created ({type(exc).__name__}: {_text(exc)})"
        except BaseException:  # KeyboardInterrupt/SystemExit: release what exists, then let it propagate
            self._release(proc, parent_conn)
            if child_conn is not None:
                child_conn.close()
            raise
        finally:
            if child_conn is not None:
                try:
                    child_conn.close()  # the parent keeps only its own end
                except OSError:
                    pass
        if reason is None:
            self._proc, self._conn = proc, parent_conn
            try:
                if not parent_conn.poll(self.startup_timeout_sec):
                    reason = f"planner worker did not become ready within {self.startup_timeout_sec:g}s"
                else:
                    kind, value, _ = parse_message(parent_conn.recv_bytes(MAX_MESSAGE_BYTES))
                    if kind == "startup_error":
                        reason = f"planner worker failed to start: {value}"
                    elif kind != "ready":
                        reason = f"unexpected startup message {kind!r}"
            except (EOFError, OSError):
                reason = "planner worker exited during startup"
            except ProtocolError as exc:
                reason = f"planner worker sent an invalid startup message: {exc}"
        startup_ns = time.perf_counter_ns() - t0
        if reason is None:
            return True, startup_ns, None
        self._fail_unavailable(reason)
        cleanup_ns = self._reap() if self._proc is not None else self._release(proc, parent_conn)
        return False, startup_ns, cleanup_ns

    def _release(self, proc: Any, conn: Any) -> int:
        """Terminate/kill/join a process and close its pipe end. Returns elapsed ns."""
        t0 = time.perf_counter_ns()
        if proc is not None:
            pid = proc.pid
            try:
                if proc.is_alive():
                    proc.terminate()
                    proc.join(self.grace_sec)
                if proc.is_alive():
                    proc.kill()
                    proc.join(self.grace_sec)
            except (ValueError, OSError, AssertionError):
                pass  # never started / already closed
            alive = False
            try:
                alive = proc.is_alive()
            except (ValueError, AssertionError):
                alive = False
            if alive:
                # Could not be reclaimed: keep the handle and pid, and stop creating new workers.
                self.stats["workers_not_reaped"] += 1
                self._unreaped_procs.append(proc)
                if pid is not None:
                    self.unreaped_pids.append(pid)
                self.unavailable = self.unavailable or f"planner worker pid {pid} could not be terminated; no further workers are started"
            else:
                try:
                    proc.join(0)
                    proc.close()
                except (ValueError, OSError, AssertionError):
                    pass
                if pid is not None:
                    self.reaped_pids.append(pid)
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass
        return time.perf_counter_ns() - t0

    def _reap(self) -> int:
        proc, conn = self._proc, self._conn
        self._proc = self._conn = None
        return self._release(proc, conn)

    def close(self) -> None:
        """Stop the worker politely, make sure it is gone, and retry any worker that survived before."""
        if self._proc is not None:
            try:
                self._conn.send(None)
                self._proc.join(self.grace_sec)
                if not self._proc.is_alive():
                    self.stats["workers_stopped_normally"] += 1
            except (OSError, ValueError):
                pass
            self._reap()
        for proc in list(self._unreaped_procs):  # one more attempt at workers that survived SIGKILL
            try:
                proc.kill()
                proc.join(self.grace_sec)
                if not proc.is_alive():
                    self._unreaped_procs.remove(proc)
                    if proc.pid in self.unreaped_pids:
                        self.unreaped_pids.remove(proc.pid)
                    self.stats["workers_not_reaped"] -= 1
                    self.reaped_pids.append(proc.pid)
            except (ValueError, OSError, AssertionError):
                pass

    def __enter__(self) -> "SubprocessPlanner":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ calls
    def call(self, step_index: int, observation: Any, max_steps: int, min_safe_fuel: float) -> dict[str, Any]:
        """One recommendation request. Never raises for planner/worker/process problems.

        Returns ``status`` in {ok, invalid_action, error, timeout}; ``action`` (ok only, already a
        plain int); ``error``; and the timing fields described in the module docstring (``None`` where
        not measurable). ``status == "invalid_action"`` means the planner answered, but not with an
        integer; the action is never forwarded.
        """
        out: dict[str, Any] = {
            "status": "ok", "action": None, "error": "", "compute_ns": None, "roundtrip_ns": None,
            "ipc_ns": None, "startup_ns": None, "cleanup_ns": None, "worker_restarted": False,
        }
        if self.unavailable is not None:
            return {**out, "status": "error", "error": f"PlannerUnavailable: {self.unavailable}"}
        if self._proc is None:
            started, startup_ns, cleanup_ns = self._start()
            out.update(startup_ns=startup_ns, cleanup_ns=cleanup_ns, worker_restarted=True)
            if not started:
                return {**out, "status": "error", "error": f"PlannerUnavailable: {self.unavailable}"}
        payload = (int(step_index), np.array(observation, dtype=float, copy=True), int(max_steps), float(min_safe_fuel))
        t0 = time.perf_counter_ns()
        deadline = t0 + int(self.timeout_sec * 1e9)
        try:
            self._conn.send(payload)
            remaining = max(0.0, (deadline - time.perf_counter_ns()) / 1e9)
            answered = self._conn.poll(remaining)
            data = self._conn.recv_bytes(MAX_MESSAGE_BYTES) if answered else None
        except (EOFError, BrokenPipeError, ConnectionError):
            return self._failed(out, t0, "PlannerWorkerDied", "worker exited", died=True)
        except Exception as exc:  # noqa: BLE001 - e.g. serialisation failure, oversized/garbled reply, OS errors
            return self._failed(out, t0, "PlannerProtocolError", f"{type(exc).__name__}: {_text(exc)}", protocol=True)
        if data is None:
            out["roundtrip_ns"] = time.perf_counter_ns() - t0
            out["cleanup_ns"] = self._reap()
            self.stats["workers_killed_on_timeout"] += 1
            return {**out, "status": "timeout", "error": f"TimeoutError: no answer within {self.timeout_sec:g}s; worker terminated"}
        try:
            kind, value, compute_ns = parse_message(data)
            if kind not in ("ok", "invalid", "error"):
                raise ProtocolError(f"unexpected reply kind {kind!r}")
        except ProtocolError as exc:
            return self._failed(out, t0, "PlannerProtocolError", str(exc), protocol=True)
        out["roundtrip_ns"] = time.perf_counter_ns() - t0
        out["compute_ns"] = int(compute_ns)
        out["ipc_ns"] = max(0, out["roundtrip_ns"] - out["compute_ns"])
        if kind == "ok":
            out["action"] = int(value)
        else:
            out.update(status="invalid_action" if kind == "invalid" else "error", error=str(value))
        return out

    def _failed(self, out: dict[str, Any], t0: int, kind: str, detail: str, *, died: bool = False, protocol: bool = False) -> dict[str, Any]:
        """The conversation with the worker broke: discard the worker (the stream cannot be trusted)."""
        out["roundtrip_ns"] = time.perf_counter_ns() - t0
        if died:
            detail = f"{detail} (exitcode={self._proc.exitcode if self._proc is not None else None})"
            self.stats["workers_died"] += 1
        if protocol:
            self.stats["protocol_errors"] += 1
        out["cleanup_ns"] = self._reap()
        return {**out, "status": "error", "error": f"{kind}: {detail}"}
