# -*- coding: utf-8 -*-
"""上半身测试目录的公共前置条件。"""
from __future__ import annotations

import time

import pytest

from common1 import logger
from pytuyarobot.command_result import CommandResult


def _result_data(result):
    if isinstance(result, CommandResult):
        if not result.ok:
            raise RuntimeError(result.message or "上半身指令执行失败")
        return result.data
    return result


def _read_power_state(upper_body):
    states = _result_data(upper_body.is_upper_powered_on())
    if not isinstance(states, (list, tuple)) or len(states) != 2:
        raise RuntimeError(f"上半身上电状态格式错误: {states!r}")
    if not all(state in (0, 1, 2, False, True) for state in states):
        raise RuntimeError(f"上半身上电状态值错误: {states!r}")
    return list(states)


@pytest.fixture(scope="function", autouse=True)
def ensure_upper_body_powered_on(device):
    """每条上半身测试开始前确保左右臂均已上电。"""
    states = _read_power_state(device.upper_body)
    if states == [1, 1]:
        logger.info("上半身左右臂已上电，无需重复执行上电操作")
        return

    logger.info("上半身当前上电状态为 %s，开始执行双臂上电", states)
    _result_data(device.upper_body.upper_power_on())

    deadline = time.monotonic() + 30
    while True:
        states = _read_power_state(device.upper_body)
        if states == [1, 1]:
            logger.info("上半身左右臂上电完成")
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(f"上半身未在 30 秒内完成双臂上电: {states!r}")
        time.sleep(0.2)
