"""上半身公共动作、等待与到位判断。"""

from __future__ import annotations

import threading
import time
from typing import Any, Sequence

from .. import constants
from ..errors import (
    AgingError,
    CommunicationResponseError,
    EmptyResponseError,
)
from ..report.log_setup import logger
from .gateway import TuyaGateway


class UpperBodyDevice:
    MOTION_STARTUP_GRACE = 1.0
    MOTION_POLL_INTERVAL = 0.1
    MOTION_IDLE_CONFIRMATIONS = 2
    MOTION_STABILIZATION_DELAY = 0.2

    def __init__(self, robot: Any, gateway: TuyaGateway) -> None:
        self.robot = robot
        self.upper_body = robot.upper_body
        self.left_arm = robot.left_arm
        self.right_arm = robot.right_arm
        self.gateway = gateway

    def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return self.gateway.upper(func, *args, **kwargs)

    def blocking_jog_call(
        self, func: Any, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        raw = self.gateway.upper_blocking_raw(func, *args, **kwargs)
        status_code = getattr(raw, "status_code", None)
        data = getattr(raw, "data", raw)
        message = getattr(raw, "message", "")
        return {
            "status_code": status_code,
            "data": data,
            "message": message,
            "raw": raw,
        }

    def wait_until_stopped(
        self,
        stop_event: threading.Event,
        timeout: float,
        *,
        allow_global_stop: bool = False,
    ) -> None:
        started = time.monotonic()
        deadline = started + timeout
        observed_moving = False
        idle_count = 0
        while time.monotonic() < deadline:
            if stop_event.is_set() and not allow_global_stop:
                raise AgingError("收到全局停止信号")
            try:
                states = self.call(self.upper_body.get_upper_is_moving)
            except (
                CommunicationResponseError,
                EmptyResponseError,
                TimeoutError,
            ) as exc:
                logger.warning(
                    "运动状态读取失败，已计入丢包并继续等待 | error=%s",
                    exc,
                )
                self._wait(stop_event, allow_global_stop)
                continue
            if not isinstance(states, (list, tuple)) or len(states) != 2:
                raise AgingError(f"上半身运动状态格式错误: {states!r}")
            if not all(value in (0, 1, False, True) for value in states):
                raise AgingError(f"上半身运动状态值错误: {states!r}")
            if any(bool(value) for value in states):
                observed_moving = True
                idle_count = 0
            elif observed_moving:
                idle_count += 1
                if idle_count >= self.MOTION_IDLE_CONFIRMATIONS:
                    break
            elif time.monotonic() - started >= self.MOTION_STARTUP_GRACE:
                break
            self._wait(stop_event, allow_global_stop)
        else:
            raise TimeoutError(f"上半身在 {timeout:g} 秒内未停止")
        if self.MOTION_STABILIZATION_DELAY:
            if allow_global_stop and stop_event.is_set():
                time.sleep(self.MOTION_STABILIZATION_DELAY)
            elif stop_event.wait(self.MOTION_STABILIZATION_DELAY):
                raise AgingError("收到全局停止信号")

    def _wait(
        self, stop_event: threading.Event, allow_global_stop: bool
    ) -> None:
        if allow_global_stop and stop_event.is_set():
            time.sleep(self.MOTION_POLL_INTERVAL)
        else:
            stop_event.wait(self.MOTION_POLL_INTERVAL)

    def go_zero(
        self,
        stop_event: threading.Event,
        timeout: float,
        *,
        force: bool = False,
    ) -> None:
        if stop_event.is_set() and not force:
            raise AgingError("停止状态下不执行回零")
        self.call(self.robot.upper_go_zero, _async=True)
        self.wait_until_stopped(
            stop_event, timeout, allow_global_stop=force
        )
        actual = self.call(self.upper_body.get_upper_angles)
        self.assert_dual_vectors(
            actual,
            {"left": constants.ZERO_ANGLES, "right": constants.ZERO_ANGLES},
            constants.ANGLE_TOLERANCE,
            "双臂回零",
        )

    def move_to_coord_initial_pose(
        self,
        stop_event: threading.Event,
        timeout: float,
        arm_side: str | None = None,
    ) -> dict[str, Sequence[float]]:
        if arm_side not in (None, "left", "right"):
            raise ValueError(f"不支持的手臂标识: {arm_side!r}")
        if arm_side is None:
            self.call(
                self.robot.send_upper_angles,
                constants.COORD_INITIAL_ANGLES["left"],
                constants.SPEED,
                constants.SPEED,
                constants.COORD_INITIAL_ANGLES["right"],
                constants.SPEED,
                constants.SPEED,
                _async=True,
            )
            sides = ("left", "right")
        else:
            arm = self.left_arm if arm_side == "left" else self.right_arm
            self.call(
                arm.send_upper_angles,
                constants.COORD_INITIAL_ANGLES[arm_side],
                constants.SPEED,
                constants.SPEED,
                _async=True,
            )
            sides = (arm_side,)
        self.wait_until_stopped(stop_event, timeout)
        actual = self.call(self.upper_body.get_upper_coords)
        expected = {
            side: constants.COORD_INITIAL_COORDS[side] for side in sides
        }
        self.assert_dual_vectors(
            actual, expected, constants.COORD_TOLERANCE, "坐标初始姿态"
        )
        return actual

    @staticmethod
    def vector_error(
        actual: Sequence[Any], expected: Sequence[float]
    ) -> float:
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            raise AgingError(
                f"运动回读结构错误，期望长度 {len(expected)}，实际 {actual!r}"
            )
        return max(
            abs(float(value) - float(target))
            for value, target in zip(actual, expected)
        )

    @classmethod
    def assert_dual_vectors(
        cls,
        actual: Any,
        expected: dict[str, Sequence[float]],
        tolerance: float,
        name: str,
    ) -> float:
        if not isinstance(actual, dict):
            raise AgingError(f"{name}回读类型错误: {actual!r}")
        maximum = 0.0
        for side, target in expected.items():
            if side not in actual:
                raise AgingError(f"{name}回读缺少 {side}: {actual!r}")
            error = cls.vector_error(actual[side], target)
            maximum = max(maximum, error)
            if error > tolerance:
                raise AgingError(
                    f"{name}{side}未到位，最大偏差 {error:.3f}，"
                    f"容差 {tolerance:g}，期望 {list(target)!r}，"
                    f"实际 {actual[side]!r}"
                )
        return maximum
