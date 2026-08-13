"""头部遥测采集。"""

from __future__ import annotations

from typing import Any

from ..device.head import HeadDevice
from ..domain.context import AgingContext
from ..errors import CommunicationResponseError, EmptyResponseError
from ..report.log_setup import logger
from ..utils import head_status_has_error, numeric_values, utc_text


class HeadMonitor:
    def __init__(self, device: HeadDevice, context: AgingContext) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event

    @staticmethod
    def _recoverable(exc: BaseException) -> bool:
        return isinstance(
            exc,
            (CommunicationResponseError, EmptyResponseError, TimeoutError),
        )

    def _optional_err_status(self) -> Any:
        method = getattr(self.device.head, "get_head_err_status", None)
        if method is None:
            return {"unsupported": "get_head_err_status"}
        return self.device.call(method)

    def run(self) -> None:
        failures = 0
        # 运动模式下等上电完成后再采遥测，避免与上电确认抢同一链路
        if self.options.run_head_motion:
            logger.info("头部监控等待上电完成…")
            while not self.stop_event.is_set():
                if self.context.head_ready.wait(0.2):
                    break
            if self.stop_event.is_set():
                return
            logger.info("头部监控开始采样")
        while not self.stop_event.is_set():
            if self.context.head_blocking_motion.is_set():
                self.stop_event.wait(self.options.monitor_interval)
                continue
            try:
                readings: dict[str, Any] = {
                    "powered_on": self.device.call(
                        self.device.head.is_head_powered_on
                    ),
                    "link_enabled": bool(
                        getattr(self.device.head, "enabled", False)
                    ),
                    "angles": self.device.call(
                        self.device.head.get_head_angles
                    ),
                    "robot_status": self.device.call(
                        self.device.head.get_head_robot_status
                    ),
                    "err_status": self._optional_err_status(),
                    "speed": self.device.call(
                        self.device.head.get_head_joints_run_sp
                    ),
                    "current": self.device.call(
                        self.device.head.get_head_joints_current
                    ),
                    "temp": self.device.call(
                        self.device.head.get_head_joints_temp
                    ),
                    "moving": self.device.call(
                        self.device.head.is_head_moving
                    ),
                }
                logger.info("头部遥测读取 | readings=%r", readings)
                self.report.append(
                    "头部遥测",
                    (
                        utc_text(),
                        readings["powered_on"],
                        readings["link_enabled"],
                        readings["angles"],
                        readings["robot_status"],
                        readings["err_status"],
                        readings["speed"],
                        readings["current"],
                        readings["temp"],
                        readings["moving"],
                        "",
                    ),
                )
                self.report.count("遥测", "头部样本")
                self.report.observe_numbers(
                    "头部电流", "电流", readings["current"]
                )
                self.report.observe_numbers(
                    "头部温度", "温度", readings["temp"]
                )
                if head_status_has_error(readings["robot_status"]):
                    self.report.event(
                        "ERROR",
                        "头部",
                        "机器人错误状态",
                        f"{readings['robot_status']!r}",
                    )
                    # 仅记录；不停全局，也不因遥测错误单独停机
                failures = 0
            except Exception as exc:
                failures += 1
                try:
                    self.report.append(
                        "头部遥测",
                        (
                            utc_text(), "", "", "", "", "", "", "", "", "",
                            str(exc),
                        ),
                    )
                except Exception as append_exc:  # noqa: BLE001
                    logger.warning(
                        "头部遥测失败行写入报告失败: %s", append_exc
                    )
                self.report.event(
                    "WARNING", "头部", "状态监控", str(exc), exc
                )
                if (
                    not self._recoverable(exc)
                    and failures >= self.options.consecutive_failure_limit
                ):
                    # 头部监控连续失败：只停头部运动，不 fatal 全局
                    self.context.stop_head_motion("状态监控连续失败", exc)
                    return
            self.stop_event.wait(self.options.monitor_interval)
