"""上半身遥测采集。"""

from __future__ import annotations

from typing import Any

from ..device.upper_body import UpperBodyDevice
from ..domain.context import AgingContext
from ..errors import CommunicationResponseError, EmptyResponseError
from ..report.log_setup import logger
from ..utils import numeric_values, upper_status_has_error, utc_text


class UpperMonitor:
    def __init__(
        self, device: UpperBodyDevice, context: AgingContext
    ) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event
        self.loss_baseline: dict[int, list[float]] = {}

    @staticmethod
    def _recoverable(exc: BaseException) -> bool:
        return isinstance(
            exc,
            (CommunicationResponseError, EmptyResponseError, TimeoutError),
        )

    def run(self) -> None:
        failures = 0
        joint_id = 1
        while not self.stop_event.is_set():
            if self.context.upper_blocking_motion.is_set():
                self.stop_event.wait(self.options.monitor_interval)
                continue
            try:
                readings: dict[str, Any] = {
                    "angles": self.device.call(
                        self.device.upper_body.get_upper_angles
                    ),
                    "coords": self.device.call(
                        self.device.upper_body.get_upper_coords
                    ),
                    "current": self.device.call(
                        self.device.upper_body.get_upper_joints_current
                    ),
                    "speed": self.device.call(
                        self.device.upper_body.get_upper_joints_run_sp
                    ),
                    "encoders": self.device.call(
                        self.device.upper_body.get_upper_encoders
                    ),
                    "loss": {
                        joint_id: self.device.call(
                            self.device.upper_body.get_upper_joint_loss_count,
                            joint_id,
                        )
                    },
                    "joints_status": self.device.call(
                        self.device.upper_body.get_upper_joints_status
                    ),
                    "robot_status": self.device.call(
                        self.device.upper_body.get_upper_robot_status
                    ),
                    "moving": self.device.call(
                        self.device.upper_body.get_upper_is_moving
                    ),
                    "paused": self.device.call(
                        self.device.upper_body.get_upper_is_paused
                    ),
                }
                logger.info(
                    "上半身遥测读取 | joint_id=J%s | readings=%r",
                    joint_id,
                    readings,
                )
                self.report.append(
                    "上半身遥测",
                    (
                        utc_text(), readings["angles"], readings["coords"],
                        readings["current"], readings["speed"],
                        readings["encoders"], readings["loss"],
                        readings["joints_status"], readings["robot_status"],
                        readings["moving"], readings["paused"], "",
                    ),
                )
                self.report.count("遥测", "上半身样本")
                self.report.observe_numbers(
                    "上半身电流", "电流", readings["current"]
                )
                values = numeric_values(readings["loss"][joint_id])
                if joint_id not in self.loss_baseline:
                    self.loss_baseline[joint_id] = values
                elif len(values) == len(self.loss_baseline[joint_id]):
                    deltas = [
                        current - baseline
                        for current, baseline in zip(
                            values, self.loss_baseline[joint_id]
                        )
                    ]
                    if deltas:
                        self.report.set_max(
                            "上半身丢包",
                            f"J{joint_id}最大增量",
                            max(deltas),
                        )
                if upper_status_has_error(readings["robot_status"]):
                    self.context.fatal(
                        "上半身",
                        "机器人错误状态",
                        f"{readings['robot_status']!r}",
                    )
                    return
                failures = 0
                joint_id = 1 if joint_id == 7 else joint_id + 1
            except Exception as exc:
                failures += 1
                self.report.append(
                    "上半身遥测",
                    (utc_text(), "", "", "", "", "", "", "", "", "", "", str(exc)),
                )
                self.report.event(
                    "WARNING", "上半身", "状态监控", str(exc), exc
                )
                if (
                    not self._recoverable(exc)
                    and failures >= self.options.consecutive_failure_limit
                ):
                    self.context.fatal(
                        "上半身", "状态监控连续失败", exc
                    )
                    return
            self.stop_event.wait(self.options.monitor_interval)
