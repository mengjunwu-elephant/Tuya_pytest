"""上半身 ROS 设备封装。"""

from __future__ import annotations

import threading
import time
from typing import Any, Sequence

from .. import constants
from ..errors import AgingError, CommunicationResponseError
from ..report.log_setup import logger
from ..ros.client import RosBridge
from ..utils import poses_to_list, scoped_angles, scoped_coords


def _srv(name: str) -> Any:
    import tuyarobot_msgs.srv as srv

    return getattr(srv, name)


def _load_pose_msg() -> Any:
    import tuyarobot_msgs.msg as msg

    for candidate in (
        "CartesianPose",
        "UpperCartesianPose",
        "Pose6D",
        "UpperPose",
    ):
        if hasattr(msg, candidate):
            return getattr(msg, candidate)
    raise AgingError(
        "tuyarobot_msgs.msg 中未找到笛卡尔姿态消息类型"
        "（尝试 CartesianPose/UpperCartesianPose/Pose6D/UpperPose）"
    )


class UpperBodyDevice:
    MOTION_STARTUP_GRACE = 1.0
    MOTION_POLL_INTERVAL = 0.1
    MOTION_IDLE_CONFIRMATIONS = 2
    MOTION_STABILIZATION_DELAY = 0.2
    SUBSYSTEM = "upper"

    def __init__(self, bridge: RosBridge) -> None:
        self.bridge = bridge
        self._bus = threading.RLock()

    def upper_session(self) -> threading.RLock:
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

    def ensure_fresh_mode(self) -> None:
        req = _srv("SetInt").Request()
        req.data = int(constants.FRESH_MODE)
        self._call("/upper/set_upper_fresh_mode", _srv("SetInt"), req, kind="设置")

    def is_powered_on(self) -> list[int]:
        resp = self._call(
            "/upper/is_upper_powered_on",
            _srv("GetInts"),
            _srv("GetInts").Request(),
            require_success=False,
        )
        return [int(v) for v in list(resp.data)]

    def power_on(self) -> None:
        self._call(
            "/upper/upper_power_on",
            _srv("TuyarobotTrigger"),
            _srv("TuyarobotTrigger").Request(),
            kind="设置",
        )

    def get_angles(self, scope: str = "upper") -> dict[str, list[float]] | list[float]:
        path = f"/{scope}/get_upper_angles"
        resp = self._call(path, _srv("GetScopedFloatValues"), _srv("GetScopedFloatValues").Request())
        values = [float(v) for v in list(resp.values)]
        if scope == "upper":
            return scoped_angles(values)
        return values

    def get_coords(self, scope: str = "upper") -> dict[str, list[float]] | list[float]:
        path = f"/{scope}/get_upper_coords"
        resp = self._call(path, _srv("GetCartesianPoses"), _srv("GetCartesianPoses").Request())
        values = poses_to_list(resp.poses)
        if scope == "upper":
            return scoped_coords(values)
        return values

    def get_is_moving_pair(self) -> list[int]:
        left = self._call(
            "/left_arm/get_upper_is_moving", _srv("GetInt"), _srv("GetInt").Request()
        )
        right = self._call(
            "/right_arm/get_upper_is_moving", _srv("GetInt"), _srv("GetInt").Request()
        )
        return [int(left.data), int(right.data)]

    def get_is_paused_pair(self) -> list[int]:
        left = self._call(
            "/left_arm/get_upper_is_paused", _srv("GetInt"), _srv("GetInt").Request()
        )
        right = self._call(
            "/right_arm/get_upper_is_paused", _srv("GetInt"), _srv("GetInt").Request()
        )
        return [int(left.data), int(right.data)]

    def send_angle(
        self, scope: str, joint_id: int, angle: float, speed: int
    ) -> None:
        req = _srv("SendUpperAngle").Request()
        req.joint_id = int(joint_id)
        req.angle = float(angle)
        req.speed = int(speed)
        req.async_mode = True
        self._call(
            f"/{scope}/service/send_upper_angle",
            _srv("SendUpperAngle"),
            req,
            kind="运动",
        )

    def send_angles(
        self,
        scope: str,
        angles: Sequence[float],
        arm_speed: int,
        gripper_speed: int = 0,
        right_angles: Sequence[float] | None = None,
        right_arm_speed: int | None = None,
        right_gripper_speed: int = 0,
    ) -> None:
        if scope == "upper":
            if right_angles is None:
                raise AgingError("双臂 send_angles 需要 right_angles")
            req = _srv("MoveDualUpperAngles").Request()
            req.left_angles = [float(v) for v in angles]
            req.left_arm_speed = int(arm_speed)
            req.left_gripper_speed = int(gripper_speed)
            req.right_angles = [float(v) for v in right_angles]
            req.right_arm_speed = int(
                arm_speed if right_arm_speed is None else right_arm_speed
            )
            req.right_gripper_speed = int(right_gripper_speed)
            req.async_mode = True
            self._call(
                "/upper/service/send_upper_angles",
                _srv("MoveDualUpperAngles"),
                req,
                kind="运动",
            )
            return
        req = _srv("MoveUpperAngles").Request()
        req.angles = [float(v) for v in angles]
        req.arm_speed = int(arm_speed)
        req.gripper_speed = int(gripper_speed)
        req.async_mode = True
        self._call(
            f"/{scope}/service/send_upper_angles",
            _srv("MoveUpperAngles"),
            req,
            kind="运动",
        )

    def _make_pose(self, values: Sequence[float]) -> Any:
        pose_cls = _load_pose_msg()
        pose = pose_cls()
        for name, value in zip(
            ("x", "y", "z", "rx", "ry", "rz"), values
        ):
            if hasattr(pose, name):
                setattr(pose, name, float(value))
        return pose

    def send_coord(
        self, scope: str, coord_id: int, value: float, speed: int
    ) -> None:
        req = _srv("SendUpperCoord").Request()
        req.coord_id = int(coord_id)
        req.value = float(value)
        req.speed = int(speed)
        req.async_mode = True
        self._call(
            f"/{scope}/service/send_upper_coord",
            _srv("SendUpperCoord"),
            req,
            kind="运动",
        )

    def send_coords(
        self,
        scope: str,
        pose: Sequence[float],
        speed: int,
        right_pose: Sequence[float] | None = None,
        right_speed: int | None = None,
    ) -> None:
        if scope == "upper":
            if right_pose is None:
                raise AgingError("双臂 send_coords 需要 right_pose")
            req = _srv("SendDualUpperCoords").Request()
            req.left_pose = self._make_pose(pose)
            req.left_speed = int(speed)
            req.right_pose = self._make_pose(right_pose)
            req.right_speed = int(speed if right_speed is None else right_speed)
            req.async_mode = True
            self._call(
                "/upper/service/send_upper_coords",
                _srv("SendDualUpperCoords"),
                req,
                kind="运动",
            )
            return
        req = _srv("SendUpperCoords").Request()
        req.poses = [self._make_pose(pose)]
        req.speeds = [int(speed)]
        req.async_mode = True
        self._call(
            f"/{scope}/service/send_upper_coords",
            _srv("SendUpperCoords"),
            req,
            kind="运动",
        )

    def upper_go_zero(self) -> None:
        req = _srv("UpperAsyncTrigger").Request()
        req.async_mode = True
        self._call("/upper/upper_go_zero", _srv("UpperAsyncTrigger"), req, kind="运动")

    def upper_stop(self) -> None:
        req = _srv("UpperAsyncTrigger").Request()
        req.async_mode = True
        self._call("/upper/upper_stop", _srv("UpperAsyncTrigger"), req, kind="运动")

    def upper_pause(self) -> None:
        req = _srv("UpperAsyncTrigger").Request()
        req.async_mode = True
        self._call("/upper/upper_pause", _srv("UpperAsyncTrigger"), req, kind="运动")

    def upper_resume(self) -> None:
        req = _srv("UpperAsyncTrigger").Request()
        req.async_mode = True
        self._call("/upper/upper_resume", _srv("UpperAsyncTrigger"), req, kind="运动")

    def wait_until_stopped(
        self,
        stop_event: threading.Event,
        timeout: float,
        *,
        allow_global_stop: bool = False,
        require_observed_motion: bool = False,
    ) -> None:
        started = time.monotonic()
        deadline = started + timeout
        observed_moving = False
        idle_count = 0
        while time.monotonic() < deadline:
            if stop_event.is_set() and not allow_global_stop:
                raise AgingError("收到全局停止信号")
            try:
                states = self.get_is_moving_pair()
            except (CommunicationResponseError, TimeoutError) as exc:
                logger.warning(
                    "运动状态读取失败，已计入丢包并继续等待 | error=%s",
                    exc,
                )
                stop_event.wait(self.MOTION_POLL_INTERVAL)
                continue
            if any(bool(value) for value in states):
                observed_moving = True
                idle_count = 0
            elif observed_moving:
                idle_count += 1
                if idle_count >= self.MOTION_IDLE_CONFIRMATIONS:
                    break
            elif (
                not require_observed_motion
                and time.monotonic() - started >= self.MOTION_STARTUP_GRACE
            ):
                break
            stop_event.wait(self.MOTION_POLL_INTERVAL)
        else:
            if require_observed_motion and not observed_moving:
                raise TimeoutError(
                    f"上半身在 {timeout:g} 秒内未进入运动状态"
                )
            raise TimeoutError(f"上半身在 {timeout:g} 秒内未停止")
        if self.MOTION_STABILIZATION_DELAY:
            if stop_event.wait(self.MOTION_STABILIZATION_DELAY):
                if not allow_global_stop:
                    raise AgingError("收到全局停止信号")

    def go_zero(
        self,
        stop_event: threading.Event,
        timeout: float,
        *,
        force: bool = False,
    ) -> None:
        if stop_event.is_set() and not force:
            raise AgingError("停止状态下不执行回零")
        self.upper_go_zero()
        self.wait_until_stopped(
            stop_event, timeout, allow_global_stop=force
        )
        actual = self.get_angles("upper")
        if not isinstance(actual, dict):
            raise AgingError(f"双臂回零回读类型错误: {actual!r}")
        expected = {
            "left": list(constants.ZERO_ANGLES["left"][:7]),
            "right": list(constants.ZERO_ANGLES["right"][:7]),
        }
        actual_joints = {
            side: list(actual[side][:7]) for side in ("left", "right")
        }
        self.assert_dual_vectors(
            actual_joints, expected, constants.ANGLE_TOLERANCE, "双臂回零"
        )

    def move_to_coord_initial_pose(
        self,
        stop_event: threading.Event,
        timeout: float,
        arm_side: str | None = None,
    ) -> None:
        if arm_side is None:
            self.send_angles(
                "upper",
                constants.COORD_INITIAL_ANGLES["left"],
                constants.SPEED,
                0,
                constants.COORD_INITIAL_ANGLES["right"],
                constants.SPEED,
                0,
            )
            sides = ("left", "right")
        else:
            scope = "left_arm" if arm_side == "left" else "right_arm"
            self.send_angles(
                scope,
                constants.COORD_INITIAL_ANGLES[arm_side],
                constants.SPEED,
                0,
            )
            sides = (arm_side,)
        self.wait_until_stopped(stop_event, timeout)
        actual = self.get_coords("upper")
        if not isinstance(actual, dict):
            raise AgingError(f"坐标初始姿态回读类型错误: {actual!r}")
        expected = {
            side: list(constants.COORD_INITIAL_COORDS[side]) for side in sides
        }
        self.assert_dual_vectors(
            {side: actual[side] for side in sides},
            expected,
            constants.COORD_TOLERANCE,
            "坐标初始姿态",
        )

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
        *,
        gripper_tolerance: float | None = None,
    ) -> float:
        if not isinstance(actual, dict):
            raise AgingError(f"{name}回读类型错误: {actual!r}")
        maximum = 0.0
        for side, target in expected.items():
            if side not in actual:
                raise AgingError(f"{name}回读缺少 {side}: {actual!r}")
            values = actual[side]
            if not isinstance(values, (list, tuple)) or len(values) != len(target):
                raise AgingError(
                    f"运动回读结构错误，期望长度 {len(target)}，实际 {values!r}"
                )
            errors = [
                abs(float(value) - float(want))
                for value, want in zip(values, target)
            ]
            error = max(errors) if errors else 0.0
            maximum = max(maximum, error)
            for index, joint_error in enumerate(errors):
                joint_tol = tolerance
                if (
                    gripper_tolerance is not None
                    and len(target) == 8
                    and index == 7
                ):
                    joint_tol = gripper_tolerance
                if joint_error > joint_tol:
                    raise AgingError(
                        f"{name}{side}未到位，最大偏差 {error:.3f}，"
                        f"J{index + 1}偏差 {joint_error:.3f}（容差 {joint_tol:g}），"
                        f"期望 {list(target)!r}，实际 {values!r}"
                    )
        return maximum
