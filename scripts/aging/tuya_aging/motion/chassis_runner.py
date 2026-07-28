"""底盘往返和旋转老化。"""

from __future__ import annotations

import time
from typing import Any

from ..device.chassis import ChassisDevice
from ..domain.context import AgingContext
from ..domain.models import MotionOutcome
from ..errors import (
    AgingError,
    ConsecutiveMotionFailureError,
    SafetyViolationError,
)
from ..report.log_setup import logger
from ..utils import utc_text


class ChassisMotionRunner:
    def __init__(
        self, device: ChassisDevice, context: AgingContext
    ) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event
        self.cycle = 0
        self.action = 0
        self.active_start: float | None = None
        self.active_end: float | None = None

    def _next_action(self) -> int:
        self.action += 1
        return self.action

    def _segment(
        self, forward: float, rotate: float, duration: float
    ) -> None:
        action = self._next_action()
        started = time.monotonic()
        control: Any = None
        stop_result: Any = None
        failure = ""
        try:
            control = self.device.call(
                self.device.chassis.agv_wheel_control,
                forward,
                rotate,
            )
            interrupted = self.stop_event.wait(duration)
            stop_result = self.device.stop()
            if interrupted:
                raise AgingError("底盘运动收到停止信号")
            reached = True
        except (ConsecutiveMotionFailureError, SafetyViolationError):
            raise
        except Exception as exc:
            reached = False
            failure = str(exc)
            try:
                stop_result = self.device.stop()
            except Exception as stop_exc:
                self.report.event(
                    "ERROR", "底盘", "异常停止",
                    f"停止底盘失败: {stop_exc}", stop_exc,
                )
        elapsed = time.monotonic() - started
        result_data = {"control": control, "stop": stop_result}
        self.report.append(
            "底盘运动",
            (
                utc_text(), self.cycle, action,
                "agv_wheel_control/agv_wheel_stop",
                forward, rotate, duration, result_data,
                "通过" if reached else "失败", failure,
            ),
        )
        self.report.count("agv_wheel_control", "调用")
        self.report.count(
            "agv_wheel_control", "成功" if reached else "失败"
        )
        self.context.policy.record_motion(
            "chassis",
            MotionOutcome(
                api="agv_wheel_control",
                target="chassis",
                command_responded=control is not None,
                motion_completed=reached,
                reached=reached,
                exceeded=False,
                expected={
                    "forward": forward,
                    "rotate": rotate,
                    "duration": duration,
                },
                actual=result_data,
                error=None,
                elapsed=elapsed,
                failure=failure,
            ),
        )
        logger.info(
            "底盘运动结果 | cycle=%s | action=%s | forward=%s"
            " | rotate=%s | duration=%s | feedback=%r | result=%s",
            self.cycle, action, forward, rotate, duration,
            result_data, "通过" if reached else "失败",
        )

    def run(self) -> None:
        logger.info("底盘运动线程启动")
        self.active_start = time.monotonic()
        segments = (
            (self.options.chassis_forward_mps, 0.0),
            (-self.options.chassis_forward_mps, 0.0),
            (0.0, self.options.chassis_rotate_rads),
            (0.0, -self.options.chassis_rotate_rads),
        )
        try:
            while not self.stop_event.is_set():
                try:
                    power_state = self.device.call(
                        self.device.chassis.is_agv_powered_on
                    )
                    logger.info("底盘上电状态: %r", power_state)
                    break
                except (AgingError, TimeoutError) as exc:
                    self.report.event(
                        "WARNING", "底盘", "运动初始化",
                        f"读取失败，稍后重试: {exc}", exc,
                    )
                    self.stop_event.wait(self.options.monitor_interval)
            while not self.stop_event.is_set():
                if (
                    self.options.cycle_limit
                    and self.cycle >= self.options.cycle_limit
                ):
                    break
                self.cycle += 1
                self.report.count("运行", "底盘循环")
                for forward, rotate in segments:
                    if self.stop_event.is_set():
                        break
                    self._segment(
                        forward,
                        rotate,
                        self.options.chassis_segment_seconds,
                    )
                self.report.save()
        except Exception as exc:
            self.context.fatal("底盘", "运动线程", exc)
        finally:
            self.active_end = time.monotonic()
            try:
                self.device.stop()
            except Exception as exc:
                self.report.event(
                    "ERROR", "底盘", "线程退出", "停止底盘失败", exc
                )
            logger.info("底盘运动线程结束")
