"""Scripted planners for testing the shadow-mode time limit (test support only; not used by the CLI).

They live in an importable module (not in a test file) because the planner worker is a *spawned*
process: the factory and the planner classes must be importable by name in the child.
"""

from __future__ import annotations

import os
import time
from typing import Any


class Scripted:
    """Return ``action`` normally; misbehave at the listed step indexes.

    ``mode`` is one of: ``sleep`` (block for an hour), ``spin`` (busy loop), ``raise``, ``invalid``
    (return an out-of-range action), ``die`` (hard exit of the worker process).
    """

    name = "scripted_planner"

    def __init__(self, action: int = 1, bad_steps: tuple[int, ...] = (), mode: str = "sleep", every_step: bool = False) -> None:
        self.action = int(action)
        self.bad_steps = set(bad_steps)
        self.mode = mode
        self.every_step = every_step

    def select_action(self, env: Any, observation: Any, step_index: int) -> Any:
        if self.every_step or step_index in self.bad_steps:
            if self.mode == "sleep":
                time.sleep(3600)
            elif self.mode == "spin":
                while True:
                    pass
            elif self.mode == "raise":
                raise RuntimeError("scripted planner failure")
            elif self.mode == "invalid":
                return 99
            elif self.mode == "die":
                os._exit(3)
        return self.action


class PrevStepProbe:
    """Stateful planner: answers 1 if it has seen the previous step of this episode, else 0.

    Mimics a planner with per-episode history (like ``planner_ops_hist``) so a test can see exactly
    when the history was lost (worker restarted after a timeout).
    """

    name = "prev_step_probe"

    def __init__(self) -> None:
        self.prev: int | None = None

    def select_action(self, env: Any, observation: Any, step_index: int) -> int:
        seen_previous = step_index == 0 or self.prev == step_index - 1
        self.prev = step_index
        return 1 if seen_previous else 0


def failing_factory() -> Any:
    raise RuntimeError("scripted startup failure")


def slow_factory() -> Any:
    time.sleep(3600)
