"""不依赖 SDK、线程和报告实现的领域数据。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallOutcome:
    api: str
    subsystem: str
    kind: str
    responded: bool
    succeeded: bool
    data: Any = None
    raw: Any = None
    timeout: bool = False
    empty: bool = False
    error: str = ""
    elapsed: float = 0.0


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
