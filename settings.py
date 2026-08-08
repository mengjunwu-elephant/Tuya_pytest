# -*- coding: utf-8 -*-
"""TuyaRobot 自动化测试配置与设备入口。"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

from pytuyarobot import TuyaRobot
from pytuyarobot.command_result import CommandResult


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = "allure-results"

ROBOT_TEST_DATA_FILE = os.path.join(BASE_DIR, "test_data", "robot.xlsx")
UPPER_BODY_TEST_DATA_FILE = os.path.join(BASE_DIR, "test_data", "upper_body.xlsx")
CHASSIS_TEST_DATA_FILE = os.path.join(BASE_DIR, "test_data", "chassis.xlsx")

CASES_DIR = {
    "1": "testcases/robot",
    "2": "testcases/upper_body",
    "3": "testcases/chassis",
    "4": "testcases/head",
}

LOG_CONFIG = {
    "name": "tuya_robot",
    "filename": os.path.join(BASE_DIR, "log", "tuya_robot.log"),
    "debug": True,
    "mode": "a",
    "encoding": "utf-8",
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class TuyaConnectionConfig:
    upper_ip: str = "192.168.0.232"
    upper_port: int = 6500
    head_ip: str = "192.168.0.231"
    head_port: int = 6501
    chassis_port: str = "COM16"
    chassis_baud: int = 2_000_000
    head_auto_connect: bool = False
    chassis_auto_connect: bool = True
    apply_limits_on_init: bool = False
    debug: bool = True
    plain_return: bool = True

    @classmethod
    def from_env(cls) -> "TuyaConnectionConfig":
        return cls(
            upper_ip=os.environ.get("TUYA_ROBOT_IP", cls.upper_ip).strip()
            or cls.upper_ip,
            upper_port=_env_int("TUYA_ROBOT_PORT", cls.upper_port),
            head_ip=os.environ.get("TUYA_HEAD_IP", cls.head_ip).strip()
            or cls.head_ip,
            head_port=_env_int("TUYA_HEAD_PORT", cls.head_port),
            chassis_port=os.environ.get(
                "TUYA_CHASSIS_PORT", cls.chassis_port
            ).strip()
            or cls.chassis_port,
            chassis_baud=_env_int("TUYA_CHASSIS_BAUD", cls.chassis_baud),
            head_auto_connect=_env_bool(
                "TUYA_HEAD_AUTO_CONNECT", cls.head_auto_connect
            ),
            chassis_auto_connect=_env_bool(
                "TUYA_CHASSIS_AUTO_CONNECT", cls.chassis_auto_connect
            ),
            apply_limits_on_init=_env_bool(
                "TUYA_APPLY_LIMITS_ON_INIT", cls.apply_limits_on_init
            ),
            debug=_env_bool("TUYA_DEBUG", cls.debug),
            plain_return=_env_bool("TUYA_PLAIN_RETURN", cls.plain_return),
        )


class TuyaRobotBase:
    """整机测试设备，集中暴露 TuyaRobot 的各个子系统。"""

    speed = 50
    angle_tolerance = 0.2
    coord_tolerance = 0.5
    head_speed = 40
    UPPER_BODY_ZERO_ANGLES = (0.0,) * 8
    COORD_MOTION_INITIAL_ANGLES = {
        "left": (-89.99, 39.99, 0.0, -100.0, 0.0, 0.0, 0.02, 0.0),
        "right": (90.0, 39.99, 0.0, -100.0, 0.03, 0.0, 0.0, 0.0),
    }
    COORD_MOTION_INITIAL_COORDS = {
        "left": (519.4, 160.2, 7.5, 97.77, 9.15, -49.36),
        "right": (519.7, -160.6, 7.3, -97.73, 9.18, 49.29),
    }
    UPPER_BODY_JOINT_SOFT_LIMITS = {
        1: (-150.0, 176.0),
        2: (-72.0, 125.0),
        3: (-163.0, 167.0),
        4: (-149.0, 1.0),
        5: (-179.0, 148.0),
        6: (-87.0, 42.0),
        7: (-80.0, 92.0),
    }
    UPPER_BODY_COORD_SOFT_LIMITS = {
        1: (-650.0, 650.0),
        2: (-841.0, 841.0),
        3: (-636.0, 665.0),
        4: (-180.0, 180.0),
        5: (-180.0, 180.0),
        6: (-180.0, 180.0),
    }
    ROBOT_TEST_DATA_FILE = ROBOT_TEST_DATA_FILE
    UPPER_BODY_TEST_DATA_FILE = UPPER_BODY_TEST_DATA_FILE
    CHASSIS_TEST_DATA_FILE = CHASSIS_TEST_DATA_FILE
    HEAD_TEST_DATA_FILE = os.path.join(BASE_DIR, "test_data", "head.xlsx")

    def __init__(self, config: Optional[TuyaConnectionConfig] = None) -> None:
        self.config = config or TuyaConnectionConfig.from_env()
        self.robot = TuyaRobot(
            self.config.upper_ip,
            self.config.upper_port,
            head_ip=self.config.head_ip,
            head_port=self.config.head_port,
            chassis_port=self.config.chassis_port,
            chassis_baud=self.config.chassis_baud,
            head_auto_connect=self.config.head_auto_connect,
            chassis_auto_connect=self.config.chassis_auto_connect,
            apply_limits_on_init=self.config.apply_limits_on_init,
            debug=self.config.debug,
            plain_return=self.config.plain_return,
        )
        self.upper_body = self.robot.upper_body
        self.left_arm = self.robot.left_arm
        self.right_arm = self.robot.right_arm
        self.head = self.robot.head
        self.chassis = self.robot.chassis

    @staticmethod
    def result_data(result):
        """统一提取左臂、右臂和整臂接口的业务返回数据。"""
        if isinstance(result, CommandResult):
            if not result.ok:
                raise RuntimeError(result.message or "TuyaRobot command failed")
            return result.data
        return result

    def go_zero(self, timeout: float = 30.0):
        """以已确认的零位关节角度驱动双臂回零并等待运动完成。"""
        result = self.robot.send_upper_angles(
            self.UPPER_BODY_ZERO_ANGLES,
            self.speed,
            self.speed,
            self.UPPER_BODY_ZERO_ANGLES,
            self.speed,
            self.speed,
            _async=False,
        )
        self.result_data(result)
        self.wait_upper(timeout=timeout)
        return result

    def go_arm_zero(self, arm_side: str, timeout: float = 30.0):
        """以已确认的零位关节角度驱动指定单臂回零并等待运动完成。"""
        if arm_side not in ("left", "right"):
            raise ValueError(f"不支持的手臂标识: {arm_side!r}")
        arm = self.left_arm if arm_side == "left" else self.right_arm
        result = arm.send_upper_angles(
            self.UPPER_BODY_ZERO_ANGLES,
            self.speed,
            self.speed,
            _async=False,
        )
        self.result_data(result)
        self.wait_upper(timeout=timeout)
        return result

    def move_to_coord_initial_pose(self, arm_side: str | None = None, timeout: float = 30.0):
        """将指定单臂或双臂移动到已确认的坐标运动初始关节姿态。"""
        if arm_side not in (None, "left", "right"):
            raise ValueError(f"不支持的手臂标识: {arm_side!r}")
        if arm_side is None:
            result = self.robot.send_upper_angles(
                self.COORD_MOTION_INITIAL_ANGLES["left"],
                self.speed,
                self.speed,
                self.COORD_MOTION_INITIAL_ANGLES["right"],
                self.speed,
                self.speed,
            )
        else:
            arm = self.left_arm if arm_side == "left" else self.right_arm
            result = arm.send_upper_angles(
                self.COORD_MOTION_INITIAL_ANGLES[arm_side],
                self.speed,
                self.speed,
            )
        self.result_data(result)
        self.wait_upper(timeout=timeout)
        if arm_side is None:
            actual = self.result_data(self.upper_body.get_upper_coords())
            if not isinstance(actual, dict) or "left" not in actual or "right" not in actual:
                raise RuntimeError(f"坐标运动初始姿态回读格式错误: {actual!r}")
            actual_by_side = actual
            target_sides = ("left", "right")
        else:
            arm = self.left_arm if arm_side == "left" else self.right_arm
            actual = self.result_data(arm.get_upper_coords())
            actual_by_side = {arm_side: actual}
            target_sides = (arm_side,)
        for target_side in target_sides:
            expected = self.COORD_MOTION_INITIAL_COORDS[target_side]
            current = actual_by_side[target_side]
            if not isinstance(current, (list, tuple)) or len(current) != 6:
                raise RuntimeError(f"{target_side} 臂坐标回读格式错误: {current!r}")
            for index, (actual_value, expected_value) in enumerate(zip(current, expected), start=1):
                if abs(float(actual_value) - expected_value) > self.coord_tolerance:
                    raise RuntimeError(
                        f"{target_side} 臂坐标轴 {index} 未到初始姿态，"
                        f"期望: {expected_value}，实际: {actual_value}"
                    )
        return actual

    def wait_upper(self, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            time.sleep(0.2) # 等待0.2秒后再次检查运动状态
            states = self.result_data(self.upper_body.get_upper_is_moving())
            if not isinstance(states, (list, tuple)) or len(states) != 2:
                raise RuntimeError(f"上半身运动状态格式错误: {states!r}")
            if not all(state in (0, 1, False, True) for state in states):
                raise RuntimeError(f"上半身运动状态值错误: {states!r}")
            if not any(bool(state) for state in states):
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(f"上半身在 {timeout:g} 秒内未停止")
            time.sleep(0.5)

    def close(self) -> None:
        self.robot.close()
