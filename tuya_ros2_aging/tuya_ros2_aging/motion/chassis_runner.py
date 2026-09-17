"""底盘往返、旋转、指示灯与升降老化（同线程串行：轮→LED→升降）。"""

from __future__ import annotations

import time
from typing import Any

from .. import constants
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
            control = self.device.wheel_control(forward, rotate)
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
        result_data = {"control": str(control), "stop": str(stop_result)}
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
            " | rotate=%s | duration=%s | result=%s",
            self.cycle, action, forward, rotate, duration,
            "通过" if reached else "失败",
        )

    def _run_led(self) -> None:
        """同循环内颜色轮转；设色失败记报告后继续下一色，不计入连续失败。"""
        for name, color in constants.CHASSIS_LED_COLORS:
            if self.stop_event.is_set():
                return
            action = self._next_action()
            started = time.monotonic()
            failure = ""
            reached = True
            try:
                self.device.set_led_color(*color)
                interrupted = self.stop_event.wait(
                    constants.CHASSIS_LED_DWELL_SECONDS
                )
                if interrupted:
                    return
            except Exception as exc:
                reached = False
                failure = str(exc)
                logger.warning(
                    "底盘LED设色失败，继续下一色 | color=%s | err=%s",
                    name, exc,
                )
            self.report.append(
                "底盘运动",
                (
                    utc_text(), self.cycle, action,
                    "set_agv_led_color",
                    name, "", constants.CHASSIS_LED_DWELL_SECONDS,
                    {"color": name, "rgb": color},
                    "通过" if reached else "失败", failure,
                ),
            )
            self.report.count("set_agv_led_color", "调用")
            self.report.count(
                "set_agv_led_color", "成功" if reached else "失败"
            )
            logger.info(
                "底盘LED | cycle=%s | action=%s | color=%s | result=%s"
                " | elapsed=%.3fs",
                self.cycle, action, name,
                "通过" if reached else "失败",
                time.monotonic() - started,
            )

    def _run_lift(self) -> None:
        """同循环内 300→500；失败记报告后继续，不计入连续失败。"""
        for lift_mm in constants.CHASSIS_LIFT_POSITIONS_MM:
            if self.stop_event.is_set():
                return
            action = self._next_action()
            started = time.monotonic()
            failure = ""
            reached = True
            result_data: Any = None
            try:
                result_data = self.device.set_lift(
                    lift_mm,
                    constants.CHASSIS_LIFT_SPEED,
                    async_mode=False,
                )
            except Exception as exc:
                reached = False
                failure = str(exc)
                logger.warning(
                    "底盘升降失败，继续下一高度 | lift_mm=%s | err=%s",
                    lift_mm, exc,
                )
            self.report.append(
                "底盘运动",
                (
                    utc_text(), self.cycle, action,
                    "set_agv_lift_control",
                    lift_mm, constants.CHASSIS_LIFT_SPEED, "",
                    {
                        "lift_mm": lift_mm,
                        "speed": constants.CHASSIS_LIFT_SPEED,
                        "async_mode": False,
                        "response": str(result_data),
                    },
                    "通过" if reached else "失败", failure,
                ),
            )
            self.report.count("set_agv_lift_control", "调用")
            self.report.count(
                "set_agv_lift_control", "成功" if reached else "失败"
            )
            logger.info(
                "底盘升降 | cycle=%s | action=%s | lift_mm=%s"
                " | result=%s | elapsed=%.3fs",
                self.cycle, action, lift_mm,
                "通过" if reached else "失败",
                time.monotonic() - started,
            )

    def _restore_led_green(self) -> None:
        try:
            self.device.set_led_color(*constants.CHASSIS_LED_RESTORE)
            logger.info("底盘LED已恢复绿色")
        except Exception as exc:
            self.report.event(
                "WARNING", "底盘", "LED恢复",
                f"恢复绿色失败: {exc}", exc,
            )

    def _restore_lift(self) -> None:
        try:
            self.device.set_lift(
                constants.CHASSIS_LIFT_RESTORE_MM,
                constants.CHASSIS_LIFT_SPEED,
                async_mode=False,
            )
            logger.info(
                "底盘升降已恢复 | lift_mm=%s",
                constants.CHASSIS_LIFT_RESTORE_MM,
            )
        except Exception as exc:
            self.report.event(
                "WARNING", "底盘", "升降恢复",
                f"恢复 {constants.CHASSIS_LIFT_RESTORE_MM}mm 失败: {exc}",
                exc,
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
                    power_state = self.device.is_powered_on()
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
                # 串行占用底盘串口：先轮段，再 LED，最后升降，避免并行超时
                for forward, rotate in segments:
                    if self.stop_event.is_set():
                        break
                    self._segment(
                        forward,
                        rotate,
                        self.options.chassis_segment_seconds,
                    )
                if not self.stop_event.is_set():
                    self._run_led()
                if not self.stop_event.is_set():
                    self._run_lift()
                self.report.save()
        except Exception as exc:
            if not self.stop_event.is_set():
                self.context.fatal("底盘", "运动线程", exc)
        finally:
            try:
                self.device.stop()
            except Exception:
                pass
            self._restore_led_green()
            self._restore_lift()
            self.active_end = time.monotonic()
            logger.info("底盘运动线程结束")
