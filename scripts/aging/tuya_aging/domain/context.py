"""线程共享但不包含业务流程的运行状态。"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

from ..config import AgingOptions


@dataclass
class AgingContext:
    options: AgingOptions
    report: Any
    policy: Any
    stop_event: threading.Event
    fatal: Callable[[str, str, BaseException | str], None]
    stop_head_motion: Callable[[str, BaseException | str], None]
    upper_blocking_motion: threading.Event
    head_blocking_motion: threading.Event
    head_stop_event: threading.Event
    head_ready: threading.Event
