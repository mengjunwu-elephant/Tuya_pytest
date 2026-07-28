"""底盘遥测和自动上报采集。"""

from __future__ import annotations

import time
from typing import Any

from ..device.chassis import ChassisDevice
from ..domain.context import AgingContext
from ..errors import AgingError, CommunicationResponseError, EmptyResponseError
from ..report.log_setup import logger
from ..utils import chassis_status_has_error, numeric_values, utc_text


class ChassisMonitor:
    def __init__(
        self, device: ChassisDevice, context: AgingContext
    ) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event
        self.original_auto_report: int | None = None
        self.loss_baseline: list[float] | None = None
        self.auto_samples: dict[str, list[float]] = {
            "100Hz": [],
            "20Hz": [],
        }

    @staticmethod
    def _recoverable(exc: BaseException) -> bool:
        return isinstance(
            exc,
            (CommunicationResponseError, EmptyResponseError, TimeoutError),
        )

    def initialize(self) -> None:
        self.original_auto_report = int(
            self.device.call(self.device.chassis.get_agv_auto_report)
        )
        if self.original_auto_report == 1:
            return
        direct_100 = self.device.call(
            self.device.chassis.get_agv_report_msg
        )
        direct_20 = self.device.call(
            self.device.chassis.get_agv_report_msg_20hz
        )
        self.report.append(
            "自动上报",
            (utc_text(), "直接查询100Hz", direct_100, "", "通过", ""),
        )
        self.report.append(
            "自动上报",
            (utc_text(), "直接查询20Hz", direct_20, "", "通过", ""),
        )
        enabled = self.device.call(
            self.device.chassis.set_agv_auto_report, 1
        )
        if enabled != 1:
            raise AgingError(f"启用底盘自动上报失败: {enabled!r}")

    def _record_auto(self, frequency: str, data: Any) -> None:
        age = None
        if isinstance(data, dict) and isinstance(
            data.get("age"), (int, float)
        ):
            age = float(data["age"])
        now = time.monotonic()
        samples = self.auto_samples[frequency]
        if samples:
            interval = now - samples[-1]
            self.report.count(
                f"自动上报{frequency}", "间隔累计秒", interval
            )
            self.report.set_max(
                f"自动上报{frequency}", "最大间隔秒", interval
            )
        samples.append(now)
        self.report.count(f"自动上报{frequency}", "样本")
        if age is not None:
            self.report.count(
                f"自动上报{frequency}", "年龄累计秒", age
            )
            self.report.set_max(
                f"自动上报{frequency}", "最大年龄秒", age
            )
        self.report.append(
            "自动上报",
            (utc_text(), frequency, data, age, "通过", ""),
        )
        logger.info(
            "底盘自动上报读取 | frequency=%s | age=%r | data=%r",
            frequency,
            age,
            data,
        )
        if chassis_status_has_error(data):
            self.context.fatal(
                "底盘", f"自动上报{frequency}错误状态", f"{data!r}"
            )

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.initialize()
                break
            except (AgingError, TimeoutError) as exc:
                self.report.event(
                    "WARNING", "底盘", "自动上报初始化",
                    f"初始化失败，稍后重试: {exc}", exc,
                )
                self.stop_event.wait(self.options.monitor_interval)
            except Exception as exc:
                self.context.fatal("底盘", "自动上报初始化", exc)
                return
        failures = 0
        while not self.stop_event.is_set():
            try:
                telemetry = {
                    "current": self.device.call(
                        self.device.chassis.get_agv_motors_current
                    ),
                    "speed": self.device.call(
                        self.device.chassis.get_agv_motors_run_sp
                    ),
                    "temp": self.device.call(
                        self.device.chassis.get_agv_motors_temp
                    ),
                    "encoder": self.device.optional_read("get_agv_encoder"),
                    "loss": self.device.call(
                        self.device.chassis.get_agv_motors_loss_count
                    ),
                    "move_state": self.device.call(
                        self.device.chassis.get_agv_move_state
                    ),
                    "joints_status": self.device.call(
                        self.device.chassis.get_agv_joints_status
                    ),
                    "robot_status": self.device.call(
                        self.device.chassis.get_agv_robot_status
                    ),
                }
                logger.info("底盘遥测读取 | telemetry=%r", telemetry)
                self.report.append(
                    "底盘遥测",
                    (
                        utc_text(), telemetry["current"],
                        telemetry["speed"], telemetry["temp"],
                        telemetry["encoder"], telemetry["loss"],
                        telemetry["move_state"], telemetry["joints_status"],
                        telemetry["robot_status"], "",
                    ),
                )
                report_100 = self.device.call(
                    self.device.chassis.get_latest_agv_report_msg,
                    self.options.auto_report_max_age,
                )
                report_20 = self.device.call(
                    self.device.chassis.get_latest_agv_report_msg_20hz,
                    self.options.auto_report_max_age,
                )
                self._record_auto("100Hz", report_100)
                self._record_auto("20Hz", report_20)
                self.report.count("遥测", "底盘样本")
                self.report.observe_numbers(
                    "底盘电流", "电流", telemetry["current"]
                )
                values = numeric_values(telemetry["loss"])
                if self.loss_baseline is None:
                    self.loss_baseline = values
                elif len(values) == len(self.loss_baseline):
                    deltas = [
                        current - baseline
                        for current, baseline in zip(
                            values, self.loss_baseline
                        )
                    ]
                    if deltas:
                        self.report.set_max(
                            "底盘丢包", "最大增量", max(deltas)
                        )
                if chassis_status_has_error(telemetry["robot_status"]):
                    self.context.fatal(
                        "底盘",
                        "机器人错误状态",
                        f"{telemetry['robot_status']!r}",
                    )
                    return
                failures = 0
            except Exception as exc:
                failures += 1
                self.report.append(
                    "底盘遥测",
                    (utc_text(), "", "", "", "", "", "", "", "", str(exc)),
                )
                self.report.event(
                    "WARNING", "底盘", "状态与自动上报监控",
                    str(exc), exc,
                )
                if (
                    not self._recoverable(exc)
                    and failures >= self.options.consecutive_failure_limit
                ):
                    self.context.fatal(
                        "底盘", "状态监控连续失败", exc
                    )
                    return
            self.stop_event.wait(self.options.monitor_interval)
