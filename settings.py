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
    upper_ip: str = "192.168.1.232"
    upper_port: int = 6500
    head_port: str = "COM4"
    head_baud: int = 115200
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
            head_port=os.environ.get("TUYA_HEAD_PORT", cls.head_port).strip()
            or cls.head_port,
            head_baud=_env_int("TUYA_HEAD_BAUD", cls.head_baud),
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
    head_speed = 40
    ROBOT_TEST_DATA_FILE = ROBOT_TEST_DATA_FILE
    UPPER_BODY_TEST_DATA_FILE = UPPER_BODY_TEST_DATA_FILE
    CHASSIS_TEST_DATA_FILE = CHASSIS_TEST_DATA_FILE

    def __init__(self, config: Optional[TuyaConnectionConfig] = None) -> None:
        self.config = config or TuyaConnectionConfig.from_env()
        self.robot = TuyaRobot(
            self.config.upper_ip,
            self.config.upper_port,
            head_port=self.config.head_port,
            head_baud=self.config.head_baud,
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
    def _result_data(result):
        if isinstance(result, CommandResult):
            if not result.ok:
                raise RuntimeError(result.message or "TuyaRobot command failed")
            return result.data
        return result

    def wait_upper(self, timeout: float = 120.0) -> None:
        deadline = time.monotonic() + timeout
        while bool(self._result_data(self.upper_body.get_upper_is_moving())):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"上半身在 {timeout:g} 秒内未停止")
            time.sleep(0.1)

    def close(self) -> None:
        self.robot.close()


# 兼容前一阶段已经使用的类名，新增代码统一使用 TuyaRobotBase。
Tuya_stm32Base = TuyaRobotBase
