# -*- coding: utf-8 -*-
import json
import time

import allure
import pytest

from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase


def _cases(sheet):
    return get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, sheet)


def _require_four_joint_sdk():
    from pytuyarobot.validation.limits import HEAD_JOINT_COUNT

    if HEAD_JOINT_COUNT != 4:
        pytest.xfail(f"当前 SDK 仅支持 {HEAD_JOINT_COUNT} 个头部关节，v1 合同要求 4 个")


@allure.feature("头部 PI4")
@allure.story("单关节运动")
@pytest.mark.head
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.parametrize("case", _cases("send_head_angle"), ids=lambda c: c["title"])
def test_send_head_angle(head, case):
    _require_four_joint_sdk()
    prompt_continue("请确认头部周围无障碍物；即将执行低速单关节运动。")
    original = head.get_head_angles()
    try:
        assert head.send_head_angle(case["joint_id"], case["angle"], case["speed"]) == case["expect_data"]
        _wait_until_stopped(head, case["timeout"])
        actual = head.get_head_angles()
        assert actual[case["joint_id"] - 1] == pytest.approx(case["angle"], abs=case["tolerance"])
        assert head.is_head_in_position(case["joint_id"], case["angle"]) == 1
    finally:
        head.send_head_angles(original, case["speed"])
        _wait_until_stopped(head, case["timeout"])


@allure.feature("头部 PI4")
@allure.story("四关节运动")
@pytest.mark.head
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.parametrize("case", _cases("send_head_angles"), ids=lambda c: c["title"])
def test_send_head_angles(head, case):
    _require_four_joint_sdk()
    prompt_continue("请确认头部周围无障碍物；即将执行低速四关节运动。")
    original = head.get_head_angles()
    target = json.loads(case["angles"])
    try:
        assert head.send_head_angles(target, case["speed"]) == case["expect_data"]
        _wait_until_stopped(head, case["timeout"])
        assert head.get_head_angles() == pytest.approx(target, abs=case["tolerance"])
    finally:
        head.send_head_angles(original, case["speed"])
        _wait_until_stopped(head, case["timeout"])


@allure.feature("头部 PI4")
@allure.story("急停保护")
@pytest.mark.head
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", _cases("send_head_angle"), ids=lambda c: f"急停保护-{c['title']}")
def test_head_emergency_stop(head, case):
    _require_four_joint_sdk()
    prompt_continue("请确认急停已释放且安全员在位；确定后开始低速动作。")
    assert head.send_head_angle(case["joint_id"], case["angle"], case["speed"]) == case["expect_data"]
    prompt_continue("请在运动期间按下急停；按下后点击确定。")
    assert head.is_head_moving() == 0
    prompt_continue("请松开急停；确认头部未自行恢复运动后点击确定。")
    assert head.is_head_moving() == 0


def _wait_until_stopped(head, timeout):
    deadline = time.monotonic() + float(timeout)
    while head.is_head_moving():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"头部在 {timeout} 秒内未停止")
        time.sleep(0.1)
