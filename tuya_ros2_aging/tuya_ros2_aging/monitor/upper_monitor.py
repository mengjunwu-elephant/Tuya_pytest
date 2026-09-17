"""上半身遥测采集。"""

from __future__ import annotations

from ..device.upper import UpperBodyDevice
from ..domain.context import AgingContext
from ..errors import CommunicationResponseError
from ..report.log_setup import logger
from ..utils import utc_text


class UpperMonitor:
    def __init__(
        self, device: UpperBodyDevice, context: AgingContext
    ) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event

    def run(self) -> None:
        from tuyarobot_msgs.srv import GetScopedFloatValues

        failures = 0
        while not self.stop_event.is_set():
            if self.context.upper_blocking_motion.is_set():
                self.stop_event.wait(self.options.monitor_interval)
                continue
            try:
                with self.device.upper_session():
                    angles = self.device.get_angles("upper")
                    coords = self.device.get_coords("upper")
                    moving = self.device.get_is_moving_pair()
                    paused = self.device.get_is_paused_pair()
                    current = self.device._call(
                        "/upper/get_upper_joints_current",
                        GetScopedFloatValues,
                        GetScopedFloatValues.Request(),
                    )
                    speed = self.device._call(
                        "/upper/get_upper_joints_run_sp",
                        GetScopedFloatValues,
                        GetScopedFloatValues.Request(),
                    )
                readings = {
                    "angles": angles,
                    "coords": coords,
                    "current": list(current.values),
                    "speed": list(speed.values),
                    "moving": moving,
                    "paused": paused,
                }
                logger.info("上半身遥测读取 | readings=%r", readings)
                self.report.append(
                    "上半身遥测",
                    (
                        utc_text(),
                        readings["angles"],
                        readings["coords"],
                        readings["current"],
                        readings["speed"],
                        "",
                        "",
                        "",
                        "",
                        readings["moving"],
                        readings["paused"],
                        "",
                    ),
                )
                self.report.count("遥测", "上半身样本")
                failures = 0
            except Exception as exc:
                failures += 1
                self.report.append(
                    "上半身遥测",
                    (
                        utc_text(), "", "", "", "", "", "", "", "",
                        "", "", str(exc),
                    ),
                )
                if not isinstance(exc, CommunicationResponseError):
                    logger.warning("上半身遥测异常: %s", exc)
                if failures >= self.options.consecutive_motion_failure_limit:
                    self.context.fatal("上半身", "遥测", exc)
                    return
            self.stop_event.wait(self.options.monitor_interval)
