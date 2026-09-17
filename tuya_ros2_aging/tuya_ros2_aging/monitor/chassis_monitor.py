"""底盘遥测采集。"""

from __future__ import annotations

from ..device.chassis import ChassisDevice
from ..domain.context import AgingContext
from ..report.log_setup import logger
from ..utils import utc_text


class ChassisMonitor:
    def __init__(
        self, device: ChassisDevice, context: AgingContext
    ) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event

    def run(self) -> None:
        failures = 0
        while not self.stop_event.is_set():
            try:
                power = self.device.is_powered_on()
                logger.info("底盘遥测 | power=%r", power)
                self.report.append(
                    "底盘遥测",
                    (utc_text(), power, ""),
                )
                self.report.count("遥测", "底盘样本")
                failures = 0
            except Exception as exc:
                failures += 1
                self.report.append(
                    "底盘遥测",
                    (utc_text(), "", str(exc)),
                )
                if failures >= self.options.consecutive_motion_failure_limit:
                    self.context.fatal("底盘", "遥测", exc)
                    return
            self.stop_event.wait(self.options.monitor_interval)
