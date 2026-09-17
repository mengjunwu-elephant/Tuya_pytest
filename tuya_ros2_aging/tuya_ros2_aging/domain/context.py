"""运行上下文。"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable

from ..config import AgingOptions
from ..report.collector import ReportCollector
from .policy import FailurePolicy


@dataclass
class AgingContext:
    options: AgingOptions
    report: ReportCollector
    policy: FailurePolicy
    stop_event: threading.Event
    fatal: Callable[[str, str, BaseException | str], None]
    stop_head_motion: Callable[[str, BaseException | str], None]
    upper_blocking_motion: threading.Event
    head_blocking_motion: threading.Event
    head_stop_event: threading.Event
    head_ready: threading.Event
