"""上半身完整老化循环。"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Iterable

from .. import constants
from ..device.upper_body import UpperBodyDevice
from ..domain.context import AgingContext
from ..domain.models import MotionOutcome
from ..errors import (
    AgingError,
    ConsecutiveMotionFailureError,
    SafetyViolationError,
)
from ..report.log_setup import logger
from ..utils import utc_text


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
        self.original_fresh_modes: Any = None
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

    def set_fresh_mode(self, target: str, mode: int) -> None:
        target_device = {
            "left": self.device.left_arm,
            "right": self.device.right_arm,
            "both": self.device.upper_body,
        }[target]
        result = self.device.call(target_device.set_upper_fresh_mode, mode)
        if result != 1:
            raise AgingError(
                f"{target} 设置刷新模式 {mode} 失败: {result!r}"
            )
        modes = self.device.call(
            self.device.upper_body.get_upper_fresh_mode
        )
        if not isinstance(modes, (list, tuple)) or len(modes) != 2:
            raise AgingError(f"刷新模式回读格式错误: {modes!r}")
        indexes = (0, 1) if target == "both" else (
            (0,) if target == "left" else (1,)
        )
        if any(int(modes[index]) != mode for index in indexes):
            raise AgingError(
                f"{target} 刷新模式不一致，期望 {mode}，实际 {modes!r}"
            )

    def ensure_powered_on(self) -> None:
        states = self.device.call(
            self.device.upper_body.is_upper_powered_on
        )
        if (
            isinstance(states, (list, tuple))
            and len(states) == 2
            and all(bool(state) for state in states)
        ):
            return
        self.device.call(self.device.upper_body.upper_power_on)
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            states = self.device.call(
                self.device.upper_body.is_upper_powered_on
            )
            if (
                isinstance(states, (list, tuple))
                and len(states) == 2
                and all(bool(state) for state in states)
            ):
                return
            if self.stop_event.wait(0.5):
                raise AgingError("上半身上电确认收到停止信号")
        raise TimeoutError(f"上半身 30 秒内未全部上电: {states!r}")

    def run_joint_limits(self) -> None:
        self.device.go_zero(
            self.stop_event, self.options.upper_timeout
        )
        for side, arm in (
            ("left", self.device.left_arm),
            ("right", self.device.right_arm),
        ):
            for joint_id, limits in constants.JOINT_SOFT_LIMITS.items():
                if self.stop_event.is_set():
                    return
                self.device.call(arm.set_upper_fresh_mode, 0)
                for boundary, target_value in (
                    ("下限", limits[0]),
                    ("上限", limits[1]),
                ):
                    params = {
                        "joint_id": joint_id,
                        "boundary": boundary,
                        "speed": self.options.upper_speed,
                    }

                    def operation(
                        arm: Any = arm,
                        joint_id: int = joint_id,
                        target_value: float = target_value,
                        limits: tuple[float, float] = limits,
                    ) -> tuple[Any, float, bool, bool]:
                        self.device.call(
                            arm.send_upper_angle,
                            joint_id,
                            target_value,
                            self.options.upper_speed,
                            _async=True,
                        )
                        self.device.wait_until_stopped(
                            self.stop_event, self.options.jog_timeout
                        )
                        angles = self.device.call(arm.get_upper_angles)
                        if not isinstance(angles, (list, tuple)) or len(angles) != 8:
                            raise AgingError(
                                f"{side}臂角度回读格式错误: {angles!r}"
                            )
                        value = float(angles[joint_id - 1])
                        error = abs(value - target_value)
                        exceeded = (
                            value < limits[0] - self.options.angle_tolerance
                            or value
                            > limits[1] + self.options.angle_tolerance
                        )
                        return (
                            value,
                            error,
                            error <= self.options.angle_tolerance and not exceeded,
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
                self.device.go_zero(
                    self.stop_event, self.options.upper_timeout
                )

    def run_angle_groups(self) -> None:
        for mode in constants.ACTIVE_FRESH_MODES:
            for target in ("left", "right", "both"):
                if self.stop_event.is_set():
                    return
                self.device.go_zero(
                    self.stop_event, self.options.upper_timeout
                )
                self.set_fresh_mode(target, mode)
                for group in constants.ANGLE_GROUPS:
                    expected = {
                        side: group[side]
                        for side in (
                            (target,) if target != "both"
                            else ("left", "right")
                        )
                    }

                    def operation(
                        group: dict[str, Any] = group,
                        target: str = target,
                    ) -> tuple[Any, float, bool, bool]:
                        if target == "left":
                            self.device.call(
                                self.device.left_arm.send_upper_angles,
                                group["left"], group["speed"], 0,
                                _async=True,
                            )
                        elif target == "right":
                            self.device.call(
                                self.device.right_arm.send_upper_angles,
                                group["right"], group["speed"], 0,
                                _async=True,
                            )
                        else:
                            self.device.call(
                                self.device.upper_body.send_upper_angles,
                                group["left"], group["speed"], 0,
                                group["right"], group["speed"], 0,
                                _async=True,
                            )
                        self.device.wait_until_stopped(
                            self.stop_event, self.options.upper_timeout
                        )
                        actual = self.device.call(
                            self.device.upper_body.get_upper_angles
                        )
                        error = self.device.assert_dual_vectors(
                            actual, expected,
                            self.options.angle_tolerance,
                            "三组角度运动",
                        )
                        return actual, error, True, False

                    self._attempt(
                        "send_upper_angles",
                        target,
                        {
                            "group": group["group"],
                            "mode": mode,
                            "speed": group["speed"],
                        },
                        expected,
                        operation,
                    )
                logger.info(
                    "send_upper_angles 三组完成，统一回零 | target=%s",
                    target,
                )
                self.device.go_zero(
                    self.stop_event, self.options.upper_timeout
                )

    def run_coord_groups(self) -> None:
        for mode in constants.ACTIVE_FRESH_MODES:
            for target in ("left", "right", "both"):
                if self.stop_event.is_set():
                    return
                self.device.move_to_coord_initial_pose(
                    self.stop_event, self.options.upper_timeout
                )
                self.set_fresh_mode(target, mode)
                for group in constants.COORD_GROUPS:
                    expected = {
                        side: group[side]
                        for side in (
                            (target,) if target != "both"
                            else ("left", "right")
                        )
                    }

                    def operation(
                        group: dict[str, Any] = group,
                        target: str = target,
                    ) -> tuple[Any, float, bool, bool]:
                        if target == "left":
                            self.device.call(
                                self.device.left_arm.send_upper_coords,
                                group["left"], group["speed"], _async=True,
                            )
                        elif target == "right":
                            self.device.call(
                                self.device.right_arm.send_upper_coords,
                                group["right"], group["speed"], _async=True,
                            )
                        else:
                            self.device.call(
                                self.device.upper_body.send_upper_coords,
                                group["left"], group["speed"],
                                group["right"], group["speed"],
                                _async=True,
                            )
                        self.device.wait_until_stopped(
                            self.stop_event, self.options.upper_timeout
                        )
                        actual = self.device.call(
                            self.device.upper_body.get_upper_coords
                        )
                        error = self.device.assert_dual_vectors(
                            actual, expected,
                            self.options.coord_tolerance,
                            "三组坐标运动",
                        )
                        return actual, error, True, False

                    self._attempt(
                        "send_upper_coords",
                        target,
                        {
                            "group": group["group"],
                            "mode": mode,
                            "speed": group["speed"],
                        },
                        expected,
                        operation,
                    )
                logger.info(
                    "send_upper_coords 三组完成，统一回零 | target=%s",
                    target,
                )
                self.device.go_zero(
                    self.stop_event, self.options.upper_timeout
                )

        self.set_fresh_mode("both", 0)
        for group in constants.COORD_GROUPS:
            if self.stop_event.is_set():
                return
            self.device.move_to_coord_initial_pose(
                self.stop_event, self.options.upper_timeout
            )
            expected = {"left": group["left"], "right": group["right"]}

            def alias_operation(
                group: dict[str, Any] = group,
            ) -> tuple[Any, float, bool, bool]:
                self.device.call(
                    self.device.upper_body.write_upper_coords,
                    group["left"], group["speed"],
                    group["right"], group["speed"],
                    _async=True,
                )
                self.device.wait_until_stopped(
                    self.stop_event, self.options.upper_timeout
                )
                actual = self.device.call(
                    self.device.upper_body.get_upper_coords
                )
                error = self.device.assert_dual_vectors(
                    actual, expected,
                    self.options.coord_tolerance,
                    "全坐标别名运动",
                )
                return actual, error, True, False

            self._attempt(
                "write_upper_coords",
                "both",
                {"group": group["group"], "speed": group["speed"]},
                expected,
                alias_operation,
            )
            self.device.go_zero(
                self.stop_event, self.options.upper_timeout
            )

    def run_single_coords(self) -> None:
        for mode in constants.ACTIVE_FRESH_MODES:
            for side, arm in (
                ("left", self.device.left_arm),
                ("right", self.device.right_arm),
            ):
                for coord_id in range(1, 7):
                    for delta in (-10.0, 10.0):
                        if self.stop_event.is_set():
                            return
                        self.device.move_to_coord_initial_pose(
                            self.stop_event, self.options.upper_timeout
                        )
                        self.set_fresh_mode(side, mode)
                        target_value = (
                            constants.COORD_INITIAL_COORDS[side][coord_id - 1]
                            + delta
                        )

                        def operation(
                            arm: Any = arm,
                            coord_id: int = coord_id,
                            target_value: float = target_value,
                        ) -> tuple[Any, float, bool, bool]:
                            self.device.call(
                                arm.send_upper_coord,
                                coord_id, target_value,
                                self.options.upper_speed,
                                _async=True,
                            )
                            self.device.wait_until_stopped(
                                self.stop_event,
                                self.options.upper_timeout,
                            )
                            coords = self.device.call(arm.get_upper_coords)
                            if not isinstance(coords, (list, tuple)):
                                raise AgingError(
                                    f"{side}臂坐标格式错误: {coords!r}"
                                )
                            value = float(coords[coord_id - 1])
                            error = abs(value - target_value)
                            return (
                                value, error,
                                error <= self.options.coord_tolerance,
                                False,
                            )

                        self._attempt(
                            "send_upper_coord",
                            side,
                            {
                                "coord_id": coord_id,
                                "delta": delta,
                                "mode": mode,
                                "speed": self.options.upper_speed,
                            },
                            target_value,
                            operation,
                        )
        if self.stop_event.is_set():
            return
        logger.info("send_upper_coord 全部单轴动作完成，统一回零")
        self.device.go_zero(
            self.stop_event, self.options.upper_timeout
        )
        action = self._next_action()
        reason = "write_upper_coord 双臂共同绝对坐标尚未确认"
        self._record(
            action, "write_upper_coord", "both",
            {"coord_id": 6, "value": None},
            "待确认", "", None, 0.0, False, False, reason, skip=True,
        )

    def run_jog_angles(self) -> None:
        targets = (
            ("left", self.device.left_arm),
            ("right", self.device.right_arm),
            ("both", self.device.upper_body),
        )
        self.set_fresh_mode("both", 0)
        self.device.go_zero(
            self.stop_event, self.options.upper_timeout
        )
        for target, api_owner in targets:
            for joint_id, limits in constants.JOINT_SOFT_LIMITS.items():
                for direction in (0, 1):
                    if self.stop_event.is_set():
                        return
                    # 双臂不跑 J2 正向；单臂 J2 正向前需先将 J1 运动到 50°
                    if joint_id == 2 and direction == 1 and target == "both":
                        logger.info(
                            "跳过 upper_jog_angle 双臂J2正向"
                        )
                        continue
                    self.set_fresh_mode("both", 0)
                    expected_value = limits[direction]

                    def operation(
                        api_owner: Any = api_owner,
                        joint_id: int = joint_id,
                        direction: int = direction,
                        limits: tuple[float, float] = limits,
                        target: str = target,
                    ) -> tuple[Any, float, bool, bool]:
                        if joint_id == 2 and direction == 1:
                            self.device.call(
                                api_owner.send_upper_angle,
                                1,
                                50.0,
                                self.options.upper_speed,
                                _async=False,
                            )
                            self.device.wait_until_stopped(
                                self.stop_event, self.options.upper_timeout
                            )
                        self.device.call(
                            api_owner.upper_jog_angle,
                            joint_id, direction, self.options.jog_speed,
                            _async=True,
                        )
                        self.device.wait_until_stopped(
                            self.stop_event, self.options.jog_timeout
                        )
                        actual = self.device.call(
                            self.device.upper_body.get_upper_angles
                        )
                        sides = (
                            ("left", "right")
                            if target == "both" else (target,)
                        )
                        values = {
                            side: float(actual[side][joint_id - 1])
                            for side in sides
                        }
                        error = max(
                            abs(value - expected_value)
                            for value in values.values()
                        )
                        exceeded = any(
                            value
                            < limits[0] - self.options.angle_tolerance
                            or value
                            > limits[1] + self.options.angle_tolerance
                            for value in values.values()
                        )
                        return (
                            values, error,
                            error <= self.options.angle_tolerance
                            and not exceeded,
                            exceeded,
                        )

                    self._attempt(
                        "upper_jog_angle",
                        target,
                        {
                            "joint_id": joint_id,
                            "direction": direction,
                            "speed": self.options.jog_speed,
                        },
                        expected_value,
                        operation,
                    )
                # 正常 Jog 依赖软件限位自然停止，不调用 upper_stop。
                logger.info(
                    "upper_jog_angle 正负软件限位完成，统一回零"
                    " | target=%s | joint_id=%s",
                    target,
                    joint_id,
                )
                self.device.go_zero(
                    self.stop_event, self.options.upper_timeout
                )

    def run_jog_increments(self) -> None:
        targets = (
            ("left", self.device.left_arm),
            ("right", self.device.right_arm),
            ("both", self.device.upper_body),
        )
        self.set_fresh_mode("both", 0)
        self.device.go_zero(
            self.stop_event, self.options.upper_timeout
        )
        for target, api_owner in targets:
            for joint_id in range(1, 8):
                if self.stop_event.is_set():
                    return
                self.set_fresh_mode("both", 0)
                increment = -5.0 if joint_id == 4 else 30.0

                def operation(
                    api_owner: Any = api_owner,
                    joint_id: int = joint_id,
                    increment: float = increment,
                ) -> tuple[Any, float, bool, bool]:
                    self.device.call(
                        api_owner.upper_jog_angle_increment,
                        joint_id, increment, self.options.jog_speed,
                        _async=True,
                    )
                    self.device.wait_until_stopped(
                        self.stop_event, self.options.upper_timeout
                    )
                    actual = self.device.call(
                        self.device.upper_body.get_upper_angles
                    )
                    sides = (
                        ("left", "right")
                        if target == "both" else (target,)
                    )
                    values = {
                        side: float(actual[side][joint_id - 1])
                        for side in sides
                    }
                    expected = {
                        side: float(constants.ZERO_ANGLES[side][joint_id - 1])
                        + increment
                        for side in sides
                    }
                    error = max(
                        abs(values[side] - expected[side]) for side in sides
                    )
                    return (
                        values, error,
                        error <= self.options.angle_tolerance, False,
                    )

                expected_log = {
                    side: float(constants.ZERO_ANGLES[side][joint_id - 1])
                    + increment
                    for side in (("left", "right") if target == "both" else (target,))
                }
                self._attempt(
                    "upper_jog_angle_increment",
                    target,
                    {
                        "joint_id": joint_id,
                        "increment": increment,
                        "speed": self.options.jog_speed,
                    },
                    expected_log,
                    operation,
                )
                logger.info(
                    "upper_jog_angle_increment 单动作完成，回零"
                    " | target=%s | joint_id=%s",
                    target,
                    joint_id,
                )
                self.device.go_zero(
                    self.stop_event, self.options.upper_timeout
                )

    def run_jog_coords(self) -> None:
        targets: tuple[tuple[str, Any, Iterable[int]], ...] = (
            ("left", self.device.left_arm, range(1, 7)),
            ("right", self.device.right_arm, range(1, 7)),
            ("both", self.device.upper_body, (3,)),
        )
        for target, api_owner, coord_ids in targets:
            for coord_id in coord_ids:
                for direction in (0, 1):
                    if self.stop_event.is_set():
                        return
                    self.set_fresh_mode("both", 0)
                    self.device.move_to_coord_initial_pose(
                        self.stop_event,
                        self.options.upper_timeout,
                        None if target == "both" else target,
                    )

                    def operation(
                        api_owner: Any = api_owner,
                        coord_id: int = coord_id,
                        direction: int = direction,
                    ) -> tuple[Any, None, bool, bool]:
                        result_box: dict[str, Any] = {}
                        finished = threading.Event()

                        def blocking_call() -> None:
                            try:
                                result_box["result"] = (
                                    self.device.blocking_jog_call(
                                        api_owner.upper_jog_coord,
                                        coord_id,
                                        direction,
                                        self.options.jog_speed,
                                        _async=False,
                                    )
                                )
                            except BaseException as exc:
                                result_box["exception"] = exc
                            finally:
                                finished.set()

                        self.context.upper_blocking_motion.set()
                        thread = threading.Thread(
                            target=blocking_call,
                            name=f"CoordJog-{target}-{coord_id}-{direction}",
                            daemon=True,
                        )
                        thread.start()
                        deadline = time.monotonic() + self.options.jog_timeout
                        try:
                            while not finished.wait(0.2):
                                if self.stop_event.is_set():
                                    self.device.call(
                                        self.device.upper_body.upper_stop
                                    )
                                    raise AgingError(
                                        "坐标 Jog 收到全局停止信号"
                                    )
                                if time.monotonic() >= deadline:
                                    self.device.call(
                                        self.device.upper_body.upper_stop
                                    )
                                    raise TimeoutError(
                                        f"坐标 Jog {self.options.jog_timeout:g}"
                                        " 秒内未结束"
                                    )
                            if "exception" in result_box:
                                raise result_box["exception"]
                            result = result_box.get("result", {})
                            raw = result.get("raw")
                            status_code = result.get("status_code")
                            data = result.get("data")
                            message = result.get("message", "")
                            if status_code is None and raw == 32:
                                status_code = 32
                            if status_code != 32 and data != 32:
                                raise AgingError(
                                    "坐标 Jog 未以状态码 32 自然结束，"
                                    f"返回 {raw!r}"
                                )
                            actual = self.device.call(
                                api_owner.get_upper_coords
                            )
                            return (
                                {"coords": actual, "message": message},
                                None, True, False,
                            )
                        finally:
                            self.context.upper_blocking_motion.clear()

                    self._attempt(
                        "upper_jog_coord",
                        target,
                        {
                            "coord_id": coord_id,
                            "direction": direction,
                            "speed": self.options.jog_speed,
                        },
                        {"status_code": 32},
                        operation,
                    )
                    self.device.go_zero(
                        self.stop_event, self.options.upper_timeout
                    )

    def run_coord_increments(self) -> None:
        targets: tuple[tuple[str, Any, Iterable[int]], ...] = (
            ("left", self.device.left_arm, range(1, 7)),
            ("right", self.device.right_arm, range(1, 7)),
            ("both", self.device.upper_body, (3,)),
        )
        for target, api_owner, coord_ids in targets:
            for coord_id in coord_ids:
                if self.stop_event.is_set():
                    return
                self.set_fresh_mode("both", 0)
                self.device.move_to_coord_initial_pose(
                    self.stop_event,
                    self.options.upper_timeout,
                    None if target == "both" else target,
                )
                before = self.device.call(
                    self.device.upper_body.get_upper_coords
                )
                increment = 30.0

                def operation(
                    api_owner: Any = api_owner,
                    coord_id: int = coord_id,
                    before: Any = before,
                ) -> tuple[Any, float, bool, bool]:
                    self.device.call(
                        api_owner.upper_jog_coord_increment,
                        coord_id, increment, self.options.jog_speed,
                        _async=True,
                    )
                    self.device.wait_until_stopped(
                        self.stop_event, self.options.upper_timeout
                    )
                    actual = self.device.call(
                        self.device.upper_body.get_upper_coords
                    )
                    sides = (
                        ("left", "right")
                        if target == "both" else (target,)
                    )
                    deltas = {
                        side: float(actual[side][coord_id - 1])
                        - float(before[side][coord_id - 1])
                        for side in sides
                    }
                    error = max(
                        abs(value - increment) for value in deltas.values()
                    )
                    return (
                        deltas, error,
                        error <= self.options.coord_tolerance, False,
                    )

                self._attempt(
                    "upper_jog_coord_increment",
                    target,
                    {
                        "coord_id": coord_id,
                        "increment": increment,
                        "speed": self.options.jog_speed,
                    },
                    increment,
                    operation,
                )
        if self.stop_event.is_set():
            return
        logger.info("upper_jog_coord_increment 全部动作完成，统一回零")
        self.device.go_zero(
            self.stop_event, self.options.upper_timeout
        )

    def run_motion_controls(self) -> None:
        self.set_fresh_mode("both", 0)
        self.device.go_zero(
            self.stop_event, self.options.upper_timeout
        )

        def operation() -> tuple[Any, None, bool, bool]:
            self.device.call(
                self.device.upper_body.send_upper_angle,
                1, 10.0, self.options.upper_speed, _async=True,
            )
            self.stop_event.wait(0.2)
            pause = self.device.call(self.device.upper_body.upper_pause)
            paused = self.device.call(
                self.device.upper_body.get_upper_is_paused
            )
            resume = self.device.call(self.device.upper_body.upper_resume)
            self.stop_event.wait(0.2)
            stop = self.device.call(self.device.upper_body.upper_stop)
            self.device.wait_until_stopped(
                self.stop_event, self.options.upper_timeout
            )
            return (
                {
                    "pause": pause, "paused": paused,
                    "resume": resume, "stop": stop,
                },
                None, True, False,
            )

        self._attempt(
            "upper_pause/upper_resume/upper_stop",
            "both",
            {"joint_id": 1, "target": 10.0},
            "暂停、恢复、停止成功",
            operation,
        )
        self.device.go_zero(
            self.stop_event, self.options.upper_timeout
        )

    def run(self) -> None:
        logger.info("上半身运动线程启动")
        self.active_start = time.monotonic()
        try:
            while not self.stop_event.is_set():
                try:
                    self.ensure_powered_on()
                    self.original_fresh_modes = self.device.call(
                        self.device.upper_body.get_upper_fresh_mode
                    )
                    self.set_fresh_mode("both", 0)
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
                ("单关节软件限位", self.run_joint_limits),
                ("三组关节角度", self.run_angle_groups),
                ("三组坐标", self.run_coord_groups),
                ("单轴坐标", self.run_single_coords),
                # ("关节Jog", self.run_jog_angles),
                ("关节增量", self.run_jog_increments),
                ("坐标Jog", self.run_jog_coords),
                ("坐标增量", self.run_coord_increments),
                ("暂停恢复停止", self.run_motion_controls),
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
