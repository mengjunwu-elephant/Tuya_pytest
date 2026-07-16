# -*- coding: utf-8 -*-
"""TuyaRobot pytest 全局配置与设备生命周期。"""
from __future__ import annotations

import os

import pytest

from settings import TuyaConnectionConfig, TuyaRobotBase


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("tuya-robot")
    group.addoption("--tuya-ip", default=None, help="上半身控制器 IP")
    group.addoption("--tuya-port", type=int, default=None, help="上半身 TCP 端口")
    group.addoption("--head-port", default=None, help="头部串口")
    group.addoption("--head-baud", type=int, default=None, help="头部波特率")
    group.addoption("--chassis-port", default=None, help="底盘串口")
    group.addoption("--chassis-baud", type=int, default=None, help="底盘波特率")
    group.addoption(
        "--connect-head", action="store_true", default=False, help="连接头部串口"
    )
    group.addoption(
        "--no-connect-chassis",
        action="store_true",
        default=False,
        help="不连接底盘串口",
    )
    group.addoption(
        "--run-hardware", action="store_true", default=False, help="运行真机测试"
    )
    group.addoption(
        "--run-motion", action="store_true", default=False, help="允许运动测试"
    )
    group.addoption(
        "--run-manual", action="store_true", default=False, help="运行人工确认测试"
    )
    group.addoption(
        "--run-danger", action="store_true", default=False, help="运行高风险测试"
    )
    group.addoption(
        "--run-firmware", action="store_true", default=False, help="运行固件测试"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    gates = {
        "hardware": config.getoption("--run-hardware") or _env_enabled("RUN_TUYA_HARDWARE"),
        "motion": config.getoption("--run-motion") or _env_enabled("RUN_TUYA_MOTION"),
        "manual": config.getoption("--run-manual") or _env_enabled("RUN_TUYA_MANUAL"),
        "danger": config.getoption("--run-danger") or _env_enabled("RUN_TUYA_DANGER"),
        "firmware": config.getoption("--run-firmware") or _env_enabled("RUN_TUYA_FIRMWARE"),
    }
    for item in items:
        path = str(getattr(item, "path", "")).replace("\\", "/")
        if "/testcases/" in path or path.startswith("testcases/"):
            item.add_marker(pytest.mark.hardware)
        for marker, enabled in gates.items():
            if item.get_closest_marker(marker) is not None and not enabled:
                item.add_marker(
                    pytest.mark.skip(reason=f"需要显式启用 --run-{marker}")
                )


def _connection_config(pytestconfig: pytest.Config) -> TuyaConnectionConfig:
    env = TuyaConnectionConfig.from_env()
    return TuyaConnectionConfig(
        upper_ip=pytestconfig.getoption("--tuya-ip") or env.upper_ip,
        upper_port=pytestconfig.getoption("--tuya-port") or env.upper_port,
        head_port=pytestconfig.getoption("--head-port") or env.head_port,
        head_baud=pytestconfig.getoption("--head-baud") or env.head_baud,
        chassis_port=pytestconfig.getoption("--chassis-port") or env.chassis_port,
        chassis_baud=pytestconfig.getoption("--chassis-baud") or env.chassis_baud,
        head_auto_connect=pytestconfig.getoption("--connect-head")
        or env.head_auto_connect,
        chassis_auto_connect=(
            False
            if pytestconfig.getoption("--no-connect-chassis")
            else env.chassis_auto_connect
        ),
        apply_limits_on_init=env.apply_limits_on_init,
        debug=env.debug,
        plain_return=env.plain_return,
    )


@pytest.fixture(scope="session")
def device(pytestconfig: pytest.Config):
    """每次测试会话只创建一个整机连接。"""
    dev = TuyaRobotBase(_connection_config(pytestconfig))
    yield dev
    dev.close()


@pytest.fixture(scope="session")
def robot(device: TuyaRobotBase):
    return device.robot


@pytest.fixture(scope="session")
def upper_body(device: TuyaRobotBase):
    return device.upper_body


@pytest.fixture(scope="session")
def left_arm(device: TuyaRobotBase):
    return device.left_arm


@pytest.fixture(scope="session")
def right_arm(device: TuyaRobotBase):
    return device.right_arm


@pytest.fixture(scope="session")
def head(device: TuyaRobotBase):
    if not device.head.enabled:
        pytest.skip("头部串口未连接；请使用 --connect-head")
    return device.head


@pytest.fixture(scope="session")
def chassis(device: TuyaRobotBase):
    if not device.chassis.enabled:
        pytest.skip("底盘串口未连接")
    return device.chassis
