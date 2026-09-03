# -*- coding: utf-8 -*-
"""头部 PI4 独立 TCP 会话。"""
from __future__ import annotations

import os

import pytest

from pytuyarobot.devices.head import Head


def _enabled(pytestconfig: pytest.Config) -> bool:
    return pytestconfig.getoption("--connect-head") or os.environ.get(
        "TUYA_HEAD_AUTO_CONNECT", ""
    ).strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def head(pytestconfig: pytest.Config):
    """仅为头部套件建立 TCP 连接，不创建整机、上半身或底盘连接。"""
    if not _enabled(pytestconfig):
        pytest.skip("头部 TCP 未启用；请使用 --connect-head")
    ip = pytestconfig.getoption("--head-ip") or os.environ.get(
        "TUYA_HEAD_IP", "192.168.0.231"
    )
    port = pytestconfig.getoption("--head-port") or int(
        os.environ.get("TUYA_HEAD_PORT", "6501")
    )
    device = Head(ip, port, auto_connect=True, plain_return=True)
    if not device.enabled:
        pytest.skip(f"头部 TCP 连接失败：{ip}:{port}")
    yield device
    device.close()
