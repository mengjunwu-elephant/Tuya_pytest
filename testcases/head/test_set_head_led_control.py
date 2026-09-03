# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

import ast

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "set_head_led_control")

@allure.feature("头部 PI4")
@allure.story("设置耳朵 LED")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.reset
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_head_led_control(head, case):
    prompt_continue("请记录当前 LED 状态；确定后执行控制。")
    args = [case[key] for key in ("mode", "r", "g", "b", "brightness", "side", "frequency_ms")]
    try:
        assert head.set_head_led_control(*args) == case["expect_data"]
        prompt_continue("请人工确认 LED 颜色、亮度和侧别。")
    finally:
        assert case["restore_value"], "Excel 必须提供 LED 恢复参数"
        assert head.set_head_led_control(*ast.literal_eval(f"({case['restore_value']},)")) == 1
