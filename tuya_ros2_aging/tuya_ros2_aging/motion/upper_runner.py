"""上半身完整老化循环（ROS2，无 Jog/增量）。"""

from __future__ import annotations

import time
from typing import Any, Callable

from .. import constants
from ..device.upper import UpperBodyDevice
from ..domain.context import AgingContext
from ..domain.models import MotionOutcome
from ..errors import (
    AgingError,
    ConsecutiveMotionFailureError,
    SafetyViolationError,
)
from ..report.log_setup import logger
from ..utils import utc_text

SCOPE = {"left": "left_arm", "right": "right_arm", "both": "upper"}


class UpperMotionRunner:
    def __init__(
        self, device: UpperBodyDevice, context: AgingContext
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
        apply_policy: bool = True,
    ) -> None:
        result = "跳过" if skip else ("通过" if reached else "失败")
        logger.info(
            "上半身运动结果 | cycle=%s | action=%s | api=%s"
            " | target=%s | params=%r | expected=%r | actual=%r"
            " | error=%r | elapsed=%.3fs | reached=%s"
            " | exceeded=%s | result=%s | failure=%s",
            self.cycle, action, api, target, params, expected, actual,
            error, elapsed, reached, exceeded, result, failure,
        )
        self.report.append(
            "上半身运动",
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
        if apply_policy:
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
            self.context.policy.record_motion("upper", outcome)
        if exceeded:
            raise SafetyViolationError(
                f"{api}/{target} 检测到软件限位越界: {actual!r}"
            )

    def _attempt(
        self,
        api: str,
        target: str,
        params: Any,
        expected: Any,
        operation: Callable[[], tuple[Any, float | None, bool, bool]],
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
            )
            return False
        self._record(
            action, api, target, params, expected, actual, error,
            time.monotonic() - started, reached, exceeded,
            "" if reached else "运动未达到目标",
        )
        return reached

    def _phase(self, name: str, func: Callable[[], None]) -> None:
        try:
            func()
        except (ConsecutiveMotionFailureError, SafetyViolationError):
            raise
        except (AgingError, TimeoutError) as exc:
            if self.stop_event.is_set():
                raise
            logger.warning(
                "上半身阶段异常，记录后继续 | phase=%s | error=%s",
                name,
                exc,
            )
            self.report.event(
                "WARNING", "上半身", name, f"记录后继续: {exc}", exc
            )

    def _go_zero_continue(self, *, context: str = "") -> bool:
        started = time.monotonic()
        try:
            with self.device.upper_session():
                self.device.go_zero(
                    self.stop_event, self.options.upper_timeout
                )
            return True
        except (ConsecutiveMotionFailureError, SafetyViolationError):
            raise
        except Exception as exc:
            if self.stop_event.is_set():
                raise
            action = self._next_action()
            failure = str(exc)
            logger.warning(
                "上半身回零失败，记录后继续 | context=%s | error=%s",
                context or "-",
                failure,
            )
            self._record(
                action,
                "upper_go_zero",
                "both",
                {"context": context} if context else {},
                "零位",
                "",
                None,
                time.monotonic() - started,
                False,
                False,
                failure,
                apply_policy=False,
            )
            self.report.event(
                "WARNING",
                "上半身",
                context or "回零",
                f"回零失败后继续: {failure}",
                exc,
            )
            return False

    def _prep_j1_before_j2_upper(self, side: str) -> bool:
        expected = constants.J2_UPPER_PREP_J1_ANGLE
        params = {
            "joint_id": 1,
            "purpose": "J2上限预摆",
            "speed": self.options.upper_speed,
        }
        action = self._next_action()
        started = time.monotonic()
        scope = SCOPE[side]
        try:
            with self.device.upper_session():
                self.device.send_angle(
                    scope, 1, expected, self.options.upper_speed
                )
                self.device.wait_until_stopped(
                    self.stop_event,
                    self.options.upper_timeout,
                    require_observed_motion=True,
                )
                angles = self.device.get_angles(scope)
            if not isinstance(angles, list) or len(angles) != 8:
                raise AgingError(f"{side}臂角度回读格式错误: {angles!r}")
            actual = float(angles[0])
            error = abs(actual - expected)
            if error <= self.options.angle_tolerance:
                self._record(
                    action, "send_upper_angle", side, params, expected,
                    actual, error, time.monotonic() - started, True, False,
                )
                return True
            self._record(
                action, "send_upper_angle", side, params, expected,
                actual, error, time.monotonic() - started, False, False,
                "预摆失败/已跳过", skip=True, apply_policy=False,
            )
            return False
        except (ConsecutiveMotionFailureError, SafetyViolationError):
            raise
        except Exception as exc:
            logger.warning(
                "J2上限预摆异常，跳过该臂J2上限 | target=%s | error=%s",
                side, exc,
            )
            self._record(
                action, "send_upper_angle", side, params, expected,
                "", None, time.monotonic() - started, False, False,
                "预摆失败/已跳过", skip=True, apply_policy=False,
            )
            return False

    def ensure_powered_on(self) -> None:
        states = self.device.is_powered_on()
        if len(states) == 2 and all(int(state) == 1 for state in states):
            return
        self.device.power_on()
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            states = self.device.is_powered_on()
            if len(states) == 2 and all(int(state) == 1 for state in states):
                return
            if self.stop_event.wait(0.5):
                raise AgingError("上半身上电确认收到停止信号")
        raise TimeoutError(f"上半身 30 秒内未全部上电: {states!r}")

    def run_joint_limits(self) -> None:
        self.device.ensure_fresh_mode()
        with self.device.upper_session():
            self._go_zero_continue(context="单关节软件限位-起始")
        for side in ("left", "right"):
            scope = SCOPE[side]
            for joint_id, limits in constants.JOINT_SOFT_LIMITS.items():
                if self.stop_event.is_set():
                    return
                for boundary, target_value in (
                    ("下限", limits[0]),
                    ("上限", limits[1]),
                ):
                    if (
                        joint_id == 2
                        and boundary == "上限"
                        and not self._prep_j1_before_j2_upper(side)
                    ):
                        continue
                    params = {
                        "joint_id": joint_id,
                        "boundary": boundary,
                        "speed": self.options.upper_speed,
                        "fresh_mode": constants.FRESH_MODE,
                    }

                    def operation(
                        scope: str = scope,
                        joint_id: int = joint_id,
                        target_value: float = target_value,
                        limits: tuple[float, float] = limits,
                    ) -> tuple[Any, float, bool, bool]:
                        with self.device.upper_session():
                            self.device.send_angle(
                                scope,
                                joint_id,
                                target_value,
                                self.options.upper_speed,
                            )
                            self.device.wait_until_stopped(
                                self.stop_event,
                                self.options.upper_timeout,
                                require_observed_motion=True,
                            )
                            angles = self.device.get_angles(scope)
                        if (
                            not isinstance(angles, list)
                            or len(angles) != 8
                        ):
                            raise AgingError(
                                f"{side}臂角度回读格式错误: {angles!r}"
                            )
                        value = float(angles[joint_id - 1])
                        error = abs(value - target_value)
                        exceeded = (
                            value
                            < limits[0] - self.options.angle_tolerance
                            or value
                            > limits[1] + self.options.angle_tolerance
                        )
                        return (
                            value,
                            error,
                            error <= self.options.angle_tolerance
                            and not exceeded,
                            exceeded,
                        )

                    self._attempt(
                        "send_upper_angle", side, params,
                        target_value, operation,
                    )
                logger.info(
                    "send_upper_angle 正负软件限位完成，统一回零"
                    " | target=%s | joint_id=%s",
                    side,
                    joint_id,
                )
                with self.device.upper_session():
                    self._go_zero_continue(
                        context=f"{side}-J{joint_id}"
                    )

    def run_angle_groups(self) -> None:
        """仅双臂；使用 ANGLE_GROUPS 中的两种姿态。"""
        self.device.ensure_fresh_mode()
        target = "both"
        if self.stop_event.is_set():
            return
        self._go_zero_continue(context="双臂角度-起始")
        for group in constants.ANGLE_GROUPS:
            expected = {"left": group["left"], "right": group["right"]}
            gripper_speed = int(group.get("gripper_speed", 0))

            def operation(
                group: dict[str, Any] = group,
                gripper_speed: int = gripper_speed,
            ) -> tuple[Any, float, bool, bool]:
                self.device.send_angles(
                    "upper",
                    group["left"],
                    group["speed"],
                    gripper_speed,
                    group["right"],
                    group["speed"],
                    gripper_speed,
                )
                self.device.wait_until_stopped(
                    self.stop_event, self.options.upper_timeout
                )
                actual = self.device.get_angles("upper")
                error = self.device.assert_dual_vectors(
                    actual,
                    expected,
                    self.options.angle_tolerance,
                    "双臂角度运动",
                    gripper_tolerance=constants.GRIPPER_ANGLE_TOLERANCE,
                )
                return actual, error, True, False

            self._attempt(
                "send_upper_angles",
                target,
                {
                    "group": group["group"],
                    "mode": constants.FRESH_MODE,
                    "speed": group["speed"],
                    "gripper_speed": gripper_speed,
                },
                expected,
                operation,
            )
        self._go_zero_continue(context="双臂角度-结束")
    def run_coord_groups(self) -> None:
        self.device.ensure_fresh_mode()
        for target in ("left", "right", "both"):
            if self.stop_event.is_set():
                return
            self.device.move_to_coord_initial_pose(
                self.stop_event, self.options.upper_timeout
            )
            for group in constants.COORD_GROUPS:
                expected = {
                    side: group[side]
                    for side in (
                        (target,) if target != "both" else ("left", "right")
                    )
                }

                def operation(
                    group: dict[str, Any] = group,
                    target: str = target,
                ) -> tuple[Any, float, bool, bool]:
                    scope = SCOPE[target]
                    if target == "both":
                        self.device.send_coords(
                            scope,
                            group["left"],
                            group["speed"],
                            group["right"],
                            group["speed"],
                        )
                    else:
                        self.device.send_coords(
                            scope, group[target], group["speed"]
                        )
                    self.device.wait_until_stopped(
                        self.stop_event, self.options.upper_timeout
                    )
                    actual = self.device.get_coords("upper")
                    error = self.device.assert_dual_vectors(
                        actual,
                        expected,
                        self.options.coord_tolerance,
                        "三组坐标运动",
                    )
                    return actual, error, True, False

                self._attempt(
                    "send_upper_coords",
                    target,
                    {
                        "group": group["group"],
                        "mode": constants.FRESH_MODE,
                        "speed": group["speed"],
                    },
                    expected,
                    operation,
                )
            self._go_zero_continue(context=f"三组坐标完成-{target}")

    def run_single_coords(self) -> None:
        self.device.ensure_fresh_mode()
        for side in ("left", "right"):
            if self.stop_event.is_set():
                return
            scope = SCOPE[side]
            self.device.move_to_coord_initial_pose(
                self.stop_event, self.options.upper_timeout, side
            )
            for coord_id in range(1, 7):
                for sign, label in ((1.0, "正"), (-1.0, "负")):
                    delta = 10.0 if coord_id <= 3 else 10.0
                    target_delta = sign * delta

                    def operation(
                        scope: str = scope,
                        side: str = side,
                        coord_id: int = coord_id,
                        target_delta: float = target_delta,
                    ) -> tuple[Any, float, bool, bool]:
                        before = self.device.get_coords(scope)
                        if not isinstance(before, list) or len(before) != 6:
                            raise AgingError(f"坐标回读错误: {before!r}")
                        absolute = float(before[coord_id - 1]) + target_delta
                        self.device.send_coord(
                            scope,
                            coord_id,
                            absolute,
                            self.options.upper_speed,
                        )
                        self.device.wait_until_stopped(
                            self.stop_event, self.options.upper_timeout
                        )
                        after = self.device.get_coords(scope)
                        if not isinstance(after, list) or len(after) != 6:
                            raise AgingError(f"坐标回读错误: {after!r}")
                        actual = float(after[coord_id - 1])
                        error = abs(actual - absolute)
                        return (
                            actual,
                            error,
                            error <= self.options.coord_tolerance,
                            False,
                        )

                    self._attempt(
                        "send_upper_coord",
                        side,
                        {
                            "coord_id": coord_id,
                            "direction": label,
                            "delta": target_delta,
                        },
                        target_delta,
                        operation,
                    )
            self._go_zero_continue(context=f"单轴坐标-{side}")

    def run_motion_controls(self) -> None:
        self.device.ensure_fresh_mode()
        self._go_zero_continue(context="暂停恢复停止-起始")

        def operation() -> tuple[Any, None, bool, bool]:
            self.device.send_angle(
                "upper", 1, 10.0, self.options.upper_speed
            )
            self.stop_event.wait(0.2)
            self.device.upper_pause()
            paused = self.device.get_is_paused_pair()
            self.device.upper_resume()
            self.stop_event.wait(0.2)
            self.device.upper_stop()
            self.device.wait_until_stopped(
                self.stop_event, self.options.upper_timeout
            )
            return (
                {"paused": paused},
                None,
                True,
                False,
            )

        self._attempt(
            "upper_pause/upper_resume/upper_stop",
            "both",
            {"joint_id": 1, "target": 10.0},
            "暂停、恢复、停止成功",
            operation,
        )
        self._go_zero_continue(context="暂停恢复停止-结束")

    def run(self) -> None:
        logger.info("上半身运动线程启动")
        self.active_start = time.monotonic()
        try:
            while not self.stop_event.is_set():
                try:
                    self.ensure_powered_on()
                    self.device.ensure_fresh_mode()
                    break
                except (ConsecutiveMotionFailureError, SafetyViolationError):
                    raise
                except (AgingError, TimeoutError) as exc:
                    self.report.event(
                        "WARNING", "上半身", "运动初始化",
                        f"初始化失败，稍后重试: {exc}", exc,
                    )
                    self.stop_event.wait(self.options.monitor_interval)
            phases = (
                # ("单关节软件限位", self.run_joint_limits),
                ("双臂关节角度", self.run_angle_groups),
                # ("三组坐标", self.run_coord_groups),
                # ("单轴坐标", self.run_single_coords),
                # ("暂停恢复停止", self.run_motion_controls),
            )
            while not self.stop_event.is_set():
                if (
                    self.options.cycle_limit
                    and self.cycle >= self.options.cycle_limit
                ):
                    break
                self.cycle += 1
                self.report.count("运行", "上半身循环")
                logger.info("开始上半身老化循环 %s", self.cycle)
                for name, phase in phases:
                    if self.stop_event.is_set():
                        break
                    self._phase(name, phase)
                self.report.save()
        except Exception as exc:
            if self.stop_event.is_set():
                logger.info("上半身运动线程按停止信号退出: %s", exc)
            else:
                self.context.fatal("上半身", "运动线程", exc)
        finally:
            self.active_end = time.monotonic()
            logger.info("上半身运动线程结束")
