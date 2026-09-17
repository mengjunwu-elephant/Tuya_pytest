"""头部完整老化循环。"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

from .. import constants
from ..device.head import HeadDevice
from ..domain.context import AgingContext
from ..domain.models import MotionOutcome
from ..errors import (
    AgingError,
    ConsecutiveMotionFailureError,
    SafetyViolationError,
)
from ..report.log_setup import logger
from ..utils import utc_text


class HeadMotionRunner:
    def __init__(self, device: HeadDevice, context: AgingContext) -> None:
        self.device = device
        self.context = context
        self.options = context.options
        self.report = context.report
        self.stop_event = context.stop_event
        self.head_stop_event = context.head_stop_event
        self.cycle = 0
        self.action = 0
        self.active_start: float | None = None
        self.active_end: float | None = None
        self._action_lock = threading.Lock()
        self._cycle_abort = threading.Event()

    def _stopped(self) -> bool:
        return (
            self.stop_event.is_set()
            or self.head_stop_event.is_set()
            or self._cycle_abort.is_set()
        )

    def _next_action(self) -> int:
        with self._action_lock:
            self.action += 1
            return self.action

    def _record(
        self,
        action: int,
        api: str,
        target: str,
        params: Any,
        expected: Any,
        actual: Any,
        error: float | None,
        elapsed: float,
        reached: bool,
        exceeded: bool,
        failure: str = "",
        *,
        skip: bool = False,
        count_policy: bool = True,
    ) -> None:
        result = "跳过" if skip else ("通过" if reached else "失败")
        logger.info(
            "头部运动结果 | cycle=%s | action=%s | api=%s"
            " | target=%s | params=%r | expected=%r | actual=%r"
            " | error=%r | elapsed=%.3fs | result=%s | failure=%s",
            self.cycle, action, api, target, params, expected, actual,
            error, elapsed, result, failure,
        )
        self.report.append(
            "头部运动",
            (
                utc_text(), self.cycle, action, api, target, params,
                expected, actual, error, round(elapsed, 3), reached,
                exceeded, result, failure,
            ),
        )
        self.report.count(api, "调用")
        if skip:
            self.report.count(api, "跳过")
            return
        self.report.count(api, "成功" if reached else "失败")
        if not count_policy:
            return
        self.context.policy.record_motion(
            "head",
            MotionOutcome(
                api=api,
                target=target,
                command_responded=not bool(failure),
                motion_completed=not bool(failure),
                reached=reached,
                exceeded=exceeded,
                expected=expected,
                actual=actual,
                error=error,
                elapsed=elapsed,
                failure=failure,
            ),
        )
        if exceeded:
            raise SafetyViolationError(
                f"{api}/{target} 头部越界: {actual!r}"
            )

    def _attempt(
        self,
        api: str,
        target: str,
        params: Any,
        expected: Any,
        operation: Callable[[], tuple[Any, float | None, bool, bool]],
        *,
        count_policy: bool = True,
    ) -> bool:
        action = self._next_action()
        started = time.monotonic()
        try:
            actual, error, reached, exceeded = operation()
        except (ConsecutiveMotionFailureError, SafetyViolationError):
            raise
        except Exception as exc:
            self._record(
                action, api, target, params, expected, "", None,
                time.monotonic() - started, False, False, str(exc),
                count_policy=count_policy,
            )
            return False
        self._record(
            action, api, target, params, expected, actual, error,
            time.monotonic() - started, reached, exceeded,
            "" if reached else "运动未达到目标",
            count_policy=count_policy,
        )
        return reached

    def _go_zero_continue(self, *, context: str = "") -> bool:
        started = time.monotonic()
        try:
            self.device.go_zero(
                self.stop_event,
                self.options.head_timeout,
                local_stop=self.head_stop_event,
                speed=self.options.head_speed,
            )
            return True
        except (ConsecutiveMotionFailureError, SafetyViolationError):
            raise
        except Exception as exc:
            if self._stopped():
                raise
            self._record(
                self._next_action(),
                "head_go_zero",
                "all",
                {"context": context},
                list(constants.HEAD_ZERO_ANGLES),
                "",
                None,
                time.monotonic() - started,
                False,
                False,
                str(exc),
                count_policy=False,
            )
            return False

    def ensure_powered(self) -> None:
        self.context.head_blocking_motion.set()
        try:
            states = self.device.is_powered_on()
            # 文档：非零即已上电；0 为未上电
            if int(states) == 0:
                logger.info("头部未上电，尝试 head_power_on")
                self.device.power_on()
                deadline = time.monotonic() + 30.0
                while time.monotonic() < deadline:
                    if self._stopped():
                        raise AgingError("头部上电确认收到停止信号")
                    states = self.device.is_powered_on()
                    if int(states) != 0:
                        break
                    self.stop_event.wait(0.3)
                else:
                    raise TimeoutError(f"头部 30 秒内未上电: {states!r}")
            logger.info("头部已上电 | state=%r", states)
            # 实机验证：未清错/使能时 send_head_angles 会 ACK=0
            self.device.prepare_for_motion()
            self.context.head_ready.set()
        finally:
            self.context.head_blocking_motion.clear()

    def run_full_joint_limits(self) -> None:
        tol = constants.HEAD_ANGLE_TOLERANCE
        if not self._go_zero_continue(context="全关节限位起始"):
            logger.warning("全关节限位起始回零失败，跳过本阶段")
            return
        negative = tuple(
            constants.HEAD_JOINT_SOFT_LIMITS[j][0] for j in range(1, 5)
        )
        positive = tuple(
            constants.HEAD_JOINT_SOFT_LIMITS[j][1] for j in range(1, 5)
        )
        for boundary, target in (("下限", negative), ("上限", positive)):
            if self._stopped():
                return

            def operation(
                target: tuple[float, ...] = target,
            ) -> tuple[Any, float, bool, bool]:
                self.device.send_angles(target, self.options.head_speed)
                self.device.wait_until_stopped(
                    self.stop_event,
                    self.options.head_timeout,
                    local_stop=self.head_stop_event,
                    expected=target,
                    tolerance=tol,
                )
                actual = self.device.get_angles()
                error = self.device.vector_error(actual, target)
                # 目标即为软限位；仅“越过限位外侧”记越界
                exceeded = any(
                    float(value)
                    < constants.HEAD_JOINT_SOFT_LIMITS[idx][0] - tol
                    or float(value)
                    > constants.HEAD_JOINT_SOFT_LIMITS[idx][1] + tol
                    for idx, value in enumerate(actual, start=1)
                )
                return list(actual), error, error <= tol and not exceeded, exceeded

            self._attempt(
                "send_head_angles",
                "all",
                {"boundary": boundary, "speed": self.options.head_speed},
                list(target),
                operation,
            )
        self._go_zero_continue(context="全关节限位结束")

    def run_single_joint_limits(self) -> None:
        tol = constants.HEAD_ANGLE_TOLERANCE
        if not self._go_zero_continue(context="单关节限位起始"):
            logger.warning("单关节限位起始回零失败，跳过本阶段")
            return
        for joint_id, limits in constants.HEAD_JOINT_SOFT_LIMITS.items():
            if self._stopped():
                return
            for boundary, target_value in (
                ("下限", limits[0]),
                ("上限", limits[1]),
            ):
                def operation(
                    joint_id: int = joint_id,
                    target_value: float = target_value,
                    limits: tuple[float, float] = limits,
                ) -> tuple[Any, float, bool, bool]:
                    self.device.send_angle(
                        joint_id, target_value, self.options.head_speed
                    )
                    expected = list(constants.HEAD_ZERO_ANGLES)
                    expected[joint_id - 1] = target_value
                    self.device.wait_until_stopped(
                        self.stop_event,
                        self.options.head_timeout,
                        local_stop=self.head_stop_event,
                        expected=expected,
                        tolerance=tol,
                    )
                    actual = self.device.get_angles()
                    value = float(actual[joint_id - 1])
                    error = abs(value - target_value)
                    exceeded = (
                        value < limits[0] - tol or value > limits[1] + tol
                    )
                    return (
                        value,
                        error,
                        error <= tol and not exceeded,
                        exceeded,
                    )

                self._attempt(
                    "send_head_angle",
                    f"J{joint_id}",
                    {
                        "joint_id": joint_id,
                        "boundary": boundary,
                        "speed": self.options.head_speed,
                    },
                    target_value,
                    operation,
                )
            self._go_zero_continue(context=f"单关节J{joint_id}")

    def run_led(self) -> None:
        for name, color in constants.HEAD_LED_COLORS:
            if self._stopped():
                return
            action = self._next_action()
            started = time.monotonic()
            try:
                self.device.set_led(*color)
                interrupted = self.stop_event.wait(
                    constants.HEAD_LED_DWELL_SECONDS
                )
                if interrupted or self.head_stop_event.is_set():
                    raise AgingError("LED 停留收到停止信号")
                self._record(
                    action, "set_head_led_control", name, {"color": color},
                    "亮灯", "ok", None, time.monotonic() - started,
                    True, False, count_policy=False,
                )
            except Exception as exc:
                self._record(
                    action, "set_head_led_control", name, {"color": color},
                    "亮灯", "", None, time.monotonic() - started,
                    False, False, str(exc), count_policy=False,
                )
        try:
            self.device.set_led(*constants.HEAD_LED_RESTORE)
        except Exception as exc:
            self.report.event("WARNING", "头部", "LED恢复", str(exc), exc)

    def run_animations(self) -> None:
        paths = self.options.head_animation_paths
        if not paths:
            action = self._next_action()
            self._record(
                action, "play_head_animation", "all", {},
                "有动画文件", "", None, 0.0, False, False,
                "无 pag 文件，跳过", skip=True, count_policy=False,
            )
            return
        for path in paths:
            if self._stopped():
                return
            action = self._next_action()
            started = time.monotonic()
            try:
                self.device.play_animation(Path(path))
                self.stop_event.wait(constants.HEAD_ANIMATION_SETTLE_SECONDS)
                self._record(
                    action, "play_head_animation", path.name, {"path": str(path)},
                    "播放", "ok", None, time.monotonic() - started,
                    True, False, count_policy=False,
                )
            except Exception as exc:
                self._record(
                    action, "play_head_animation", path.name, {"path": str(path)},
                    "播放", "", None, time.monotonic() - started,
                    False, False, str(exc), count_policy=False,
                )

    def run(self) -> None:
        logger.info("头部运动线程启动")
        self.active_start = time.monotonic()
        try:
            while not self.stop_event.is_set() and not self.head_stop_event.is_set():
                try:
                    self.ensure_powered()
                    break
                except (ConsecutiveMotionFailureError, SafetyViolationError) as exc:
                    self.context.stop_head_motion("运动初始化", exc)
                    return
                except (AgingError, TimeoutError) as exc:
                    self.report.event(
                        "WARNING", "头部", "运动初始化",
                        f"初始化失败，稍后重试: {exc}", exc,
                    )
                    self.stop_event.wait(self.options.monitor_interval)
            while not self._stopped():
                if (
                    self.options.cycle_limit
                    and self.cycle >= self.options.cycle_limit
                ):
                    break
                self.cycle += 1
                self._cycle_abort.clear()
                self.report.count("运行", "头部循环")
                logger.info("开始头部老化循环 %s", self.cycle)
                workers = [
                    ("关节软限位-全关节", self.run_full_joint_limits),
                    ("关节软限位-单关节", self.run_single_joint_limits),
                    ("耳朵LED", self.run_led),
                    ("屏幕动画", self.run_animations),
                ]
                # 关节串行；LED/动画可与关节并行，但为降低总线争用，本版串行执行
                for name, phase in workers:
                    if self._stopped():
                        break
                    try:
                        phase()
                    except (ConsecutiveMotionFailureError, SafetyViolationError) as exc:
                        self.context.stop_head_motion(name, exc)
                        break
                    except Exception as exc:
                        if self._stopped():
                            break
                        self.report.event(
                            "WARNING", "头部", name, f"记录后继续: {exc}", exc
                        )
                self._go_zero_continue(context="循环结束回零")
                self.report.save()
        except Exception as exc:
            if not self._stopped():
                self.context.stop_head_motion("运动线程", exc)
        finally:
            self.active_end = time.monotonic()
            logger.info("头部运动线程结束")
