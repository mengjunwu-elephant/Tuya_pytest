"""头部遥测采集。"""

from __future__ import annotations

from ..device.head import HeadDevice
from ..domain.context import AgingContext
from ..errors import CommunicationResponseError
from ..report.log_setup import logger
from ..utils import utc_text


class HeadMonitor:
    def __init__(self, device: HeadDevice, context: AgingContext) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event
        self.head_stop_event = context.head_stop_event

    def run(self) -> None:
        failures = 0
        while not (
            self.stop_event.is_set() or self.head_stop_event.is_set()
        ):
            if not self.context.head_ready.is_set():
                self.stop_event.wait(self.options.monitor_interval)
                continue
            if self.context.head_blocking_motion.is_set():
                self.stop_event.wait(self.options.monitor_interval)
                continue
            try:
                power = self.device.is_powered_on()
                angles = self.device.get_angles()
                moving = self.device.is_moving()
                logger.info(
                    "头部遥测 | power=%r angles=%r moving=%r",
                    power, angles, moving,
                )
                self.report.append(
                    "头部遥测",
                    (utc_text(), power, angles, moving, ""),
                )
                self.report.count("遥测", "头部样本")
                failures = 0
            except Exception as exc:
                failures += 1
                self.report.append(
                    "头部遥测",
                    (utc_text(), "", "", "", str(exc)),
                )
                if (
                    failures >= self.options.consecutive_motion_failure_limit
                    and not isinstance(exc, CommunicationResponseError)
                ):
                    self.context.stop_head_motion("遥测", exc)
                    return
            self.stop_event.wait(self.options.monitor_interval)
