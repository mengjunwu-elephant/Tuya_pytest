"""头部设备操作、等待与回零。"""

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


class HeadDevice:
    MOTION_STARTUP_GRACE = 1.0
    MOTION_POLL_INTERVAL = 0.1
    MOTION_IDLE_CONFIRMATIONS = 2
    MOTION_STABILIZATION_DELAY = 0.2

    def __init__(self, robot: Any, gateway: TuyaGateway) -> None:
        self.robot = robot
        self.head = robot.head
        self.gateway = gateway

    def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return self.gateway.head(func, *args, **kwargs)

    def wait_until_stopped(
        self,
        stop_event: threading.Event,
        timeout: float,
        *,
        allow_global_stop: bool = False,
        local_stop: threading.Event | None = None,
        expected: Sequence[float] | None = None,
        tolerance: float | None = None,
    ) -> None:
        """等待头部 ``is_head_moving`` 变为停止。

        仅按运动状态结束等待；未到位不追加等待，由调用方记录结果。
        ``expected``/``tolerance`` 仅用于结束时打一条未到位日志。
        """
        started = time.monotonic()
        deadline = started + timeout
        observed_moving = False
        idle_count = 0
        while time.monotonic() < deadline:
            if local_stop is not None and local_stop.is_set():
                raise AgingError("收到头部局部停止信号")
            if stop_event.is_set() and not allow_global_stop:
                raise AgingError("收到全局停止信号")
            try:
                moving = self.call(self.head.is_head_moving)
            except (
                CommunicationResponseError,
                EmptyResponseError,
                TimeoutError,
            ) as exc:
                logger.warning(
                    "头部运动状态读取失败，已计入丢包并继续等待 | error=%s",
                    exc,
                )
                self._wait(stop_event, allow_global_stop, local_stop)
                continue
            is_moving = bool(moving)
            if is_moving:
                observed_moving = True
                idle_count = 0
            elif observed_moving:
                idle_count += 1
                if idle_count >= self.MOTION_IDLE_CONFIRMATIONS:
                    self._log_miss_if_needed(expected, tolerance)
                    break
            elif time.monotonic() - started >= self.MOTION_STARTUP_GRACE:
                self._log_miss_if_needed(expected, tolerance)
                break
            self._wait(stop_event, allow_global_stop, local_stop)
        else:
            raise TimeoutError(f"头部在 {timeout:g} 秒内未停止")
        if self.MOTION_STABILIZATION_DELAY:
            if allow_global_stop and stop_event.is_set():
                time.sleep(self.MOTION_STABILIZATION_DELAY)
            elif local_stop is not None and local_stop.is_set():
                time.sleep(self.MOTION_STABILIZATION_DELAY)
            elif stop_event.wait(self.MOTION_STABILIZATION_DELAY):
                raise AgingError("收到全局停止信号")

    def _log_miss_if_needed(
        self,
        expected: Sequence[float] | None,
        tolerance: float | None,
    ) -> None:
        if expected is None or tolerance is None:
            return
        try:
            actual = self.call(self.head.get_head_angles)
            error = self.vector_error(actual, expected)
        except (
            CommunicationResponseError,
            EmptyResponseError,
            TimeoutError,
            AgingError,
        ) as exc:
            logger.warning("头部到位回读失败，仅记录 | error=%s", exc)
            return
        if error > tolerance:
            logger.info(
                "头部未到位，仅记录不追加等待"
                " | expected=%r | actual=%r | error=%.3f | tolerance=%g",
                list(expected),
                actual,
                error,
                tolerance,
            )

    def _wait(
        self,
        stop_event: threading.Event,
        allow_global_stop: bool,
        local_stop: threading.Event | None,
    ) -> None:
        if local_stop is not None and local_stop.is_set():
            time.sleep(self.MOTION_POLL_INTERVAL)
            return
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
        local_stop: threading.Event | None = None,
        speed: int | None = None,
        tolerance: float | None = None,
    ) -> None:
        if stop_event.is_set() and not force:
            raise AgingError("停止状态下不执行头部回零")
        if local_stop is not None and local_stop.is_set() and not force:
            raise AgingError("头部局部停止状态下不执行回零")
        motion_speed = constants.HEAD_SPEED if speed is None else speed
        angle_tol = (
            constants.HEAD_ANGLE_TOLERANCE
            if tolerance is None
            else tolerance
        )
        self.call(
            self.head.send_head_angles,
            constants.HEAD_ZERO_ANGLES,
            motion_speed,
            _async=True,
        )
        self.wait_until_stopped(
            stop_event,
            timeout,
            allow_global_stop=force,
            local_stop=None if force else local_stop,
            expected=constants.HEAD_ZERO_ANGLES,
            tolerance=angle_tol,
        )
        actual = self.call(self.head.get_head_angles)
        try:
            self.assert_angles(
                actual,
                constants.HEAD_ZERO_ANGLES,
                angle_tol,
                "头部回零",
            )
        except AgingError as exc:
            logger.warning("%s（仅记录，不中断）", exc)

    @staticmethod
    def vector_error(
        actual: Sequence[Any], expected: Sequence[float]
    ) -> float:
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            raise AgingError(
                f"头部角度回读结构错误，期望长度 {len(expected)}，实际 {actual!r}"
            )
        return max(
            abs(float(value) - float(target))
            for value, target in zip(actual, expected)
        )

    @classmethod
    def assert_angles(
        cls,
        actual: Any,
        expected: Sequence[float],
        tolerance: float,
        name: str,
    ) -> float:
        error = cls.vector_error(actual, expected)
        if error > tolerance:
            raise AgingError(
                f"{name}未到位，最大偏差 {error:.3f}，"
                f"容差 {tolerance:g}，期望 {list(expected)!r}，"
                f"实际 {actual!r}"
            )
        return error
