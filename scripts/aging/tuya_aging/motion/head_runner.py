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
        # 同一循环内运动/LED/动画三个子线程共享的动作编号与提前中止信号
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
            " | error=%r | elapsed=%.3fs | reached=%s"
            " | exceeded=%s | result=%s | failure=%s",
            self.cycle, action, api, target, params, expected, actual,
            error, elapsed, reached, exceeded, result, failure,
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
        if reached:
            self.report.count(api, "成功")
        else:
            self.report.count(api, "失败")
        if error is not None:
            self.report.set_max(api, "最大偏差", float(error))
        if exceeded:
            self.report.count(api, "越界")
        if not count_policy:
            return
        outcome = MotionOutcome(
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
        )
        self.context.policy.record_motion("head", outcome)
        if exceeded:
            raise SafetyViolationError(
                f"{api}/{target} 检测到头部软件限位越界: {actual!r}"
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
                action, api, target, params, expected, None, None,
                time.monotonic() - started, False, False, str(exc),
                count_policy=count_policy,
            )
            return False
        self._record(
            action, api, target, params, expected, actual, error,
            time.monotonic() - started, reached, exceeded,
            count_policy=count_policy,
        )
        return reached

    def _wait_or_stop(self, seconds: float) -> bool:
        """等待指定秒数；收到停止信号则提前返回 True。"""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._stopped():
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if self.stop_event.wait(min(0.2, remaining)):
                return True
            if self.head_stop_event.is_set():
                return True
        return self._stopped()

    def _skip(
        self, api: str, target: str, params: Any, reason: str
    ) -> None:
        action = self._next_action()
        self._record(
            action, api, target, params, None, None, None, 0.0,
            True, False, reason, skip=True,
        )

    def ensure_powered_on(self) -> None:
        """确认头部已上电：仅当 is_head_powered_on()==1 视为成功。

        head_power_on 的返回值 1 只表示指令 ACK，不代表已上电。
        上电确认期间独占头部链路，避免监控并发干扰状态查询。
        """
        self.context.head_blocking_motion.set()
        try:
            deadline = time.monotonic() + 30.0
            states: Any = None
            while time.monotonic() < deadline:
                if self._stopped():
                    raise AgingError("头部上电确认收到停止信号")
                states = self.device.call(self.device.head.is_head_powered_on)
                if int(states) == 1:
                    logger.info("头部已上电 | is_head_powered_on=%r", states)
                    self.context.head_ready.set()
                    return

                logger.warning(
                    "头部未上电，下发 head_power_on 后等待状态变为 1 | state=%r",
                    states,
                )
                ack = self.device.call(self.device.head.head_power_on)
                logger.info("head_power_on ACK=%r（不等于已上电）", ack)

                # 上电后给固件留出稳定时间，期间只轮询状态，不再连发 power_on
                settle_deadline = min(time.monotonic() + 5.0, deadline)
                while time.monotonic() < settle_deadline:
                    if self._stopped():
                        raise AgingError("头部上电确认收到停止信号")
                    if self.stop_event.wait(0.3) or self.head_stop_event.is_set():
                        raise AgingError("头部上电确认收到停止信号")
                    states = self.device.call(
                        self.device.head.is_head_powered_on
                    )
                    if int(states) == 1:
                        logger.info(
                            "头部已上电 | is_head_powered_on=%r", states
                        )
                        self.context.head_ready.set()
                        return
                    logger.info(
                        "等待头部上电生效 | is_head_powered_on=%r", states
                    )
            raise TimeoutError(f"头部 30 秒内未上电: {states!r}")
        finally:
            # 成功则保持 head_ready；失败不置 ready，监控不启动采样
            self.context.head_blocking_motion.clear()

    def run_full_joint_limits(self) -> None:
        tol = constants.HEAD_ANGLE_TOLERANCE
        self.device.go_zero(
            self.stop_event,
            self.options.head_timeout,
            local_stop=self.head_stop_event,
            speed=self.options.head_speed,
            tolerance=tol,
        )
        negative = tuple(
            constants.HEAD_JOINT_SOFT_LIMITS[joint_id][0]
            for joint_id in range(1, 5)
        )
        positive = tuple(
            constants.HEAD_JOINT_SOFT_LIMITS[joint_id][1]
            for joint_id in range(1, 5)
        )
        for boundary, target in (("下限", negative), ("上限", positive)):
            if self._stopped():
                return
            params = {
                "boundary": boundary,
                "speed": self.options.head_speed,
            }

            def operation(
                target: tuple[float, ...] = target,
            ) -> tuple[Any, float, bool, bool]:
                self.device.call(
                    self.device.head.send_head_angles,
                    target,
                    self.options.head_speed,
                    _async=True,
                )
                self.device.wait_until_stopped(
                    self.stop_event,
                    self.options.head_timeout,
                    local_stop=self.head_stop_event,
                    expected=target,
                    tolerance=tol,
                )
                actual = self.device.call(self.device.head.get_head_angles)
                error = self.device.vector_error(actual, target)
                exceeded = any(
                    float(value)
                    < constants.HEAD_JOINT_SOFT_LIMITS[idx][0] - tol
                    or float(value)
                    > constants.HEAD_JOINT_SOFT_LIMITS[idx][1] + tol
                    for idx, value in enumerate(actual, start=1)
                )
                return (
                    list(actual),
                    error,
                    error <= tol and not exceeded,
                    exceeded,
                )

            self._attempt(
                "send_head_angles", "all", params, list(target), operation,
            )
        logger.info("send_head_angles 正负软件限位完成，统一回零")
        self.device.go_zero(
            self.stop_event,
            self.options.head_timeout,
            local_stop=self.head_stop_event,
            speed=self.options.head_speed,
            tolerance=tol,
        )

    def run_single_joint_limits(self) -> None:
        tol = constants.HEAD_ANGLE_TOLERANCE
        self.device.go_zero(
            self.stop_event,
            self.options.head_timeout,
            local_stop=self.head_stop_event,
            speed=self.options.head_speed,
            tolerance=tol,
        )
        for joint_id, limits in constants.HEAD_JOINT_SOFT_LIMITS.items():
            if self._stopped():
                return
            for boundary, target_value in (
                ("下限", limits[0]),
                ("上限", limits[1]),
            ):
                params = {
                    "joint_id": joint_id,
                    "boundary": boundary,
                    "speed": self.options.head_speed,
                }

                def operation(
                    joint_id: int = joint_id,
                    target_value: float = target_value,
                    limits: tuple[float, float] = limits,
                ) -> tuple[Any, float, bool, bool]:
                    before = self.device.call(
                        self.device.head.get_head_angles
                    )
                    if (
                        not isinstance(before, (list, tuple))
                        or len(before) != 4
                    ):
                        raise AgingError(
                            f"头部角度回读格式错误: {before!r}"
                        )
                    expected = [
                        float(value) for value in before
                    ]
                    expected[joint_id - 1] = target_value
                    self.device.call(
                        self.device.head.send_head_angle,
                        joint_id,
                        target_value,
                        self.options.head_speed,
                        _async=True,
                    )
                    self.device.wait_until_stopped(
                        self.stop_event,
                        self.options.head_timeout,
                        local_stop=self.head_stop_event,
                        expected=expected,
                        tolerance=tol,
                    )
                    angles = self.device.call(self.device.head.get_head_angles)
                    if (
                        not isinstance(angles, (list, tuple))
                        or len(angles) != 4
                    ):
                        raise AgingError(
                            f"头部角度回读格式错误: {angles!r}"
                        )
                    value = float(angles[joint_id - 1])
                    error = abs(value - target_value)
                    exceeded = (
                        value < limits[0] - tol
                        or value > limits[1] + tol
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
                    params,
                    target_value,
                    operation,
                )
            logger.info(
                "send_head_angle 正负软件限位完成，统一回零 | joint_id=%s",
                joint_id,
            )
            self.device.go_zero(
                self.stop_event,
                self.options.head_timeout,
                local_stop=self.head_stop_event,
                speed=self.options.head_speed,
                tolerance=tol,
            )

    def run_led(self) -> None:
        for color_name, led_params in constants.HEAD_LED_COLORS:
            if self._stopped():
                return
            params = {"color": color_name, "led": led_params}

            def operation(
                led_params: tuple[int, ...] = led_params,
            ) -> tuple[Any, float | None, bool, bool]:
                result = self.device.call(
                    self.device.head.set_head_led_control,
                    *led_params,
                )
                if result == 1 and self._wait_or_stop(
                    constants.HEAD_LED_DWELL_SECONDS
                ):
                    return result, None, True, False
                return result, None, result == 1, False

            self._attempt(
                "set_head_led_control",
                f"ears/{color_name}",
                params,
                1,
                operation,
            )
        if self._stopped():
            return

        def restore_operation() -> tuple[Any, float | None, bool, bool]:
            restore = self.device.call(
                self.device.head.set_head_led_control,
                *constants.HEAD_LED_RESTORE,
            )
            return restore, None, restore == 1, False

        self._attempt(
            "set_head_led_control",
            "ears/restore",
            {"led": constants.HEAD_LED_RESTORE},
            1,
            restore_operation,
        )

    def run_animation(self) -> None:
        paths = self.options.head_animation_paths
        if not paths:
            self._skip(
                "play_head_animation",
                "screen",
                {"configured": False},
                "pag_file 目录不存在或无 .pag 文件，跳过动画",
            )
            return
        for path in paths:
            if self._stopped():
                return
            params = {"path": str(path)}

            def operation(
                path: Path = path,
            ) -> tuple[Any, float | None, bool, bool]:
                result = self.device.call(
                    self.device.head.play_head_animation,
                    str(path),
                )
                self._wait_or_stop(constants.HEAD_ANIMATION_SETTLE_SECONDS)
                return result, None, result == 1, False

            # 单文件失败只记报告，不计入连续运动失败停机阈值
            self._attempt(
                "play_head_animation",
                path.name,
                params,
                1,
                operation,
                count_policy=False,
            )

    def _run_joint_limits(self) -> None:
        self.run_full_joint_limits()
        if self._stopped():
            return
        self.run_single_joint_limits()

    def _run_cycle_parallel(self) -> None:
        """运动、LED、动画三者并行各跑一遍，互不等待。

        所有头部调用经 ``gateway.head_lock`` 串行化，保证同一 TCP 帧不交错；
        任一子线程遇到致命失败即置 ``_cycle_abort`` 让其余尽快退出，
        join 后按运动越界/连续失败优先重新抛出，交由 ``run`` 统一处理。
        """
        workers = (
            ("关节软件限位", self._run_joint_limits),
            ("耳朵LED", self.run_led),
            ("屏幕动画", self.run_animation),
        )
        errors: list[BaseException] = []
        errors_lock = threading.Lock()

        def make_runner(
            name: str, phase: Callable[[], None]
        ) -> Callable[[], None]:
            def runner() -> None:
                logger.info(
                    "头部并行相位开始 | cycle=%s | phase=%s",
                    self.cycle,
                    name,
                )
                try:
                    phase()
                except BaseException as exc:  # noqa: BLE001
                    with errors_lock:
                        errors.append(exc)
                    self._cycle_abort.set()
                finally:
                    logger.info(
                        "头部并行相位结束 | cycle=%s | phase=%s",
                        self.cycle,
                        name,
                    )

            return runner

        threads = [
            threading.Thread(
                target=make_runner(name, phase),
                name=f"head-{name}",
                daemon=True,
            )
            for name, phase in workers
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            for exc in errors:
                if isinstance(
                    exc,
                    (ConsecutiveMotionFailureError, SafetyViolationError),
                ):
                    raise exc
            raise errors[0]

    def run(self) -> None:
        logger.info("头部运动线程启动")
        # 立刻独占，避免监控线程在上电确认前抢占同一 TCP
        self.context.head_blocking_motion.set()
        self.active_start = time.monotonic()
        try:
            while not self._stopped():
                try:
                    self.ensure_powered_on()
                    break
                except (ConsecutiveMotionFailureError, SafetyViolationError):
                    raise
                except (AgingError, TimeoutError) as exc:
                    self.report.event(
                        "WARNING", "头部", "运动初始化",
                        f"初始化失败，稍后重试: {exc}", exc,
                    )
                    if self.stop_event.wait(self.options.monitor_interval):
                        break
                    if self.head_stop_event.is_set():
                        break
            if not self.context.head_ready.is_set():
                raise AgingError("头部未完成上电确认，不进入运动循环")
            while not self._stopped():
                if (
                    self.options.cycle_limit
                    and self.cycle >= self.options.cycle_limit
                ):
                    break
                self.cycle += 1
                self.report.count("运行", "头部循环")
                logger.info("开始头部老化循环 %s", self.cycle)
                # 关节限位运动、耳朵 LED、屏幕动画并行执行，各跑一遍
                self._cycle_abort.clear()
                self.context.head_blocking_motion.set()
                try:
                    self._run_cycle_parallel()
                finally:
                    self.context.head_blocking_motion.clear()
                if not self._stopped():
                    self.device.go_zero(
                        self.stop_event,
                        self.options.head_timeout,
                        local_stop=self.head_stop_event,
                        speed=self.options.head_speed,
                        tolerance=constants.HEAD_ANGLE_TOLERANCE,
                    )
                self.report.save()
        except (ConsecutiveMotionFailureError, SafetyViolationError) as exc:
            logger.error("头部运动达到局部停止条件: %s", exc)
            self.context.stop_head_motion("运动连续失败/越界", exc)
        except Exception as exc:
            if self._stopped():
                logger.info("头部运动线程按停止信号退出: %s", exc)
            else:
                self.context.stop_head_motion("运动线程异常", exc)
        finally:
            self.active_end = time.monotonic()
            logger.info("头部运动线程结束")
