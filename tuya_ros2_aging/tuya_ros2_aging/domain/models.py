"""领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MotionOutcome:
    api: str
    target: str
    command_responded: bool
    motion_completed: bool
    reached: bool
    exceeded: bool
    expected: Any
    actual: Any
    error: float | None
    elapsed: float
    failure: str = ""
