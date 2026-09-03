# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

import json
import time

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "send_head_angles")

@allure.feature("头部 PI4")
@allure.story("四关节运动")
@pytest.mark.head
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_send_head_angles(head, case):
    from pytuyarobot.validation.limits import HEAD_JOINT_COUNT
    if HEAD_JOINT_COUNT != 4:
        pytest.xfail(f"当前 SDK 仅支持 {HEAD_JOINT_COUNT} 个头部关节")
    prompt_continue("请确认头部周围无障碍物；即将执行低速四关节运动。")
    original = head.get_head_angles()
    target = json.loads(case["angles"])
    try:
        assert head.send_head_angles(target, case["speed"]) == case["expect_data"]
        deadline = time.monotonic() + case["timeout"]
        while head.is_head_moving():
            if time.monotonic() >= deadline:
                raise TimeoutError("头部四关节运动未在超时内停止")
            time.sleep(0.1)
        assert head.get_head_angles() == pytest.approx(target, abs=case["tolerance"])
    finally:
        head.send_head_angles(original, case["speed"])
