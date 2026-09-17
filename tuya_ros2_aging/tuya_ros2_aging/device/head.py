"""头部 ROS 设备封装。"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Sequence

from .. import constants
from ..errors import AgingError, CommunicationResponseError
from ..report.log_setup import logger
from ..ros.client import RosBridge


def _srv(name: str) -> Any:
    import tuyarobot_msgs.srv as srv

    return getattr(srv, name)


class HeadDevice:
    MOTION_STARTUP_GRACE = 1.0
    MOTION_POLL_INTERVAL = 0.1
    MOTION_IDLE_CONFIRMATIONS = 2
    MOTION_STABILIZATION_DELAY = 0.2
    SUBSYSTEM = "head"

    def __init__(self, bridge: RosBridge) -> None:
        self.bridge = bridge
        self._bus = threading.RLock()

    def session(self) -> threading.RLock:
        return self._bus

    def _call(
        self,
        name: str,
        srv_type: Any,
        request: Any,
        *,
        kind: str = "读取",
        require_success: bool = True,
    ) -> Any:
        return self.bridge.call(
            self.SUBSYSTEM,
            name,
            srv_type,
            request,
            kind=kind,
            require_success=require_success,
        )

    def is_powered_on(self) -> int:
        # 文档：data=0 时 success=false；非零表示已上电
        resp = self._call(
            "/head/is_head_powered_on",
            _srv("GetInt"),
            _srv("GetInt").Request(),
            require_success=False,
        )
        return int(resp.data)

    def power_on(self) -> None:
        try:
            self._call(
                "/head/head_power_on",
                _srv("TuyarobotTrigger"),
                _srv("TuyarobotTrigger").Request(),
                kind="设置",
            )
        except CommunicationResponseError as exc:
            logger.warning("头部上电接口不可用或失败: %s", exc)

    def clear_error(self, joint_id: int = 254) -> None:
        req = _srv("HeadJointCommand").Request()
        req.joint_id = int(joint_id)
        self._call(
            "/head/clear_head_error",
            _srv("HeadJointCommand"),
            req,
            kind="设置",
        )

    def set_joint_enable(self, joint_id: int = 254, state: int = 1) -> None:
        req = _srv("SetHeadJointEnable").Request()
        req.joint_id = int(joint_id)
        req.state = int(state)
        self._call(
            "/head/set_head_joint_enable",
            _srv("SetHeadJointEnable"),
            req,
            kind="设置",
        )

    def prepare_for_motion(self) -> None:
        """运动前清错并使能全部关节（254）。"""
        self.clear_error(254)
        self.set_joint_enable(254, 1)
        logger.info("头部已清错并使能全部关节")

    def get_angles(self) -> list[float]:
        resp = self._call(
            "/head/service/get_head_angles",
            _srv("GetScopedFloatValues"),
            _srv("GetScopedFloatValues").Request(),
        )
        return [float(v) for v in list(resp.values)]

    def is_moving(self) -> int:
        resp = self._call(
            "/head/is_head_moving",
            _srv("GetInt"),
            _srv("GetInt").Request(),
            require_success=False,
        )
        return int(resp.data)

    def send_angles(self, angles: Sequence[float], speed: int) -> None:
        req = _srv("SendHeadAngles").Request()
        req.angles = [float(v) for v in angles]
        req.speed = int(speed)
        self._call(
            "/head/send_head_angles",
            _srv("SendHeadAngles"),
            req,
            kind="运动",
        )

    def send_angle(self, joint_id: int, angle: float, speed: int) -> None:
        req = _srv("SendHeadAngle").Request()
        req.joint_id = int(joint_id)
        req.angle = float(angle)
        req.speed = int(speed)
        self._call(
            "/head/send_head_angle",
            _srv("SendHeadAngle"),
            req,
            kind="运动",
        )

    def set_led(
        self,
        mode: int,
        r: int,
        g: int,
        b: int,
        brightness: int,
        side: int,
        frequency_ms: int,
    ) -> None:
        req = _srv("SetHeadLedControl").Request()
        req.mode = int(mode)
        req.r = int(r)
        req.g = int(g)
        req.b = int(b)
        req.brightness = int(brightness)
        req.side = int(side)
        req.frequency_ms = int(frequency_ms)
        self._call(
            "/head/set_head_led_control",
            _srv("SetHeadLedControl"),
            req,
            kind="设置",
        )

    def play_animation(self, path: Path) -> None:
        req = _srv("PlayHeadAnimationUpload").Request()
        req.animation_paths = [str(path.resolve())]
        req.intervals_ms = []
        req.play_times_ms = []
        self._call(
            "/head/play_head_animation",
            _srv("PlayHeadAnimationUpload"),
            req,
            kind="设置",
        )

    def stop(self) -> None:
        self._call(
            "/head/head_stop",
            _srv("TuyarobotTrigger"),
            _srv("TuyarobotTrigger").Request(),
            kind="运动",
        )

    def wait_until_stopped(
        self,
        stop_event: threading.Event,
        timeout: float,
        *,
        local_stop: threading.Event | None = None,
        expected: Sequence[float] | None = None,
        tolerance: float = constants.HEAD_ANGLE_TOLERANCE,
    ) -> None:
        """等待 is_head_moving 变为停止。

        下发后短时间内可能仍报静止，需启动宽限；见到运动后再连续确认静止。
        expected/tolerance 仅用于结束时记录未到位日志，不追加等待。
        """
        started = time.monotonic()
        deadline = started + timeout
        observed_moving = False
        idle_count = 0
        while time.monotonic() < deadline:
            if stop_event.is_set() or (local_stop and local_stop.is_set()):
                raise AgingError("头部等待收到停止信号")
            try:
                moving = self.is_moving()
            except CommunicationResponseError as exc:
                logger.warning("头部运动状态读取失败: %s", exc)
                stop_event.wait(self.MOTION_POLL_INTERVAL)
                continue
            if int(moving) != 0:
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
            stop_event.wait(self.MOTION_POLL_INTERVAL)
        else:
            raise TimeoutError(f"头部在 {timeout:g} 秒内未停止")
        if self.MOTION_STABILIZATION_DELAY:
            if stop_event.wait(self.MOTION_STABILIZATION_DELAY):
                raise AgingError("头部等待收到停止信号")

    def _log_miss_if_needed(
        self,
        expected: Sequence[float] | None,
        tolerance: float,
    ) -> None:
        if expected is None:
            return
        try:
            actual = self.get_angles()
            error = self.vector_error(actual, expected)
        except Exception as exc:
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

    def go_zero(
        self,
        stop_event: threading.Event,
        timeout: float,
        *,
        force: bool = False,
        local_stop: threading.Event | None = None,
        speed: int = constants.HEAD_SPEED,
        tolerance: float = constants.HEAD_ANGLE_TOLERANCE,
    ) -> None:
        if stop_event.is_set() and not force:
            raise AgingError("停止状态下不执行头部回零")
        target = list(constants.HEAD_ZERO_ANGLES)
        self.send_angles(target, speed)
        self.wait_until_stopped(
            stop_event,
            timeout,
            local_stop=None if force else local_stop,
            expected=target,
            tolerance=tolerance,
        )
        actual = self.get_angles()
        error = self.vector_error(actual, target)
        if error > tolerance:
            # 与 SDK 老化一致：回零未到位只告警；由 runner 决定是否记失败
            raise AgingError(
                f"头部回零未到位，偏差 {error:.3f}，期望 {target!r}，实际 {actual!r}"
            )

    @staticmethod
    def vector_error(
        actual: Sequence[Any], expected: Sequence[float]
    ) -> float:
        if len(actual) != len(expected):
            raise AgingError(
                f"头部回读长度错误，期望 {len(expected)}，实际 {actual!r}"
            )
        return max(
            abs(float(a) - float(b)) for a, b in zip(actual, expected)
        )
