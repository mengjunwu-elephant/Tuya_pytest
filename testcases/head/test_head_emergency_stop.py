# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "send_head_angle")

@allure.feature("头部 PI4")
@allure.story("急停状态下头部运动保护")
@pytest.mark.head
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: f"急停保护-{c['title']}")
def test_head_emergency_stop(head, case):
    prompt_continue("请确认急停已释放且安全员在位；确定后开始低速动作。")
    assert head.send_head_angle(case["joint_id"], case["angle"], case["speed"]) == case["expect_data"]
    prompt_continue("请在运动期间按下急停；按下后点击确定。")
    assert head.is_head_moving() == 0
    prompt_continue("请松开急停；确认头部未自行恢复运动后点击确定。")
    assert head.is_head_moving() == 0
