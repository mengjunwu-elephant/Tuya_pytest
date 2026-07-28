# -*- coding: utf-8 -*-
import ast

import allure
import pytest

from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase


def _cases(sheet):
    return get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, sheet)


@allure.feature("头部 PI4")
@allure.story("耳朵 LED")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.reset
@pytest.mark.parametrize("case", _cases("set_head_led_control"), ids=lambda c: c["title"])
def test_set_head_led_control(head, case):
    prompt_continue("请记录当前 LED 状态；确定后执行控制。")
    args = [case[key] for key in ("mode", "r", "g", "b", "brightness", "side", "frequency_ms")]
    try:
        assert head.set_head_led_control(*args) == case["expect_data"]
        prompt_continue("请人工确认 LED 颜色、亮度和侧别。")
    finally:
        restore = case["restore_value"]
        assert restore, "Excel 必须提供 LED 恢复参数"
        assert head.set_head_led_control(*ast.literal_eval(f"({restore},)")) == 1


@allure.feature("头部 PI4")
@allure.story("屏幕动画")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.parametrize("case", _cases("play_screen_animation"), ids=lambda c: c["title"])
def test_play_screen_animation(head, case):
    if not case["chunks"]:
        pytest.skip("Excel 未提供批准的 bytes 动画数据")
    chunks = [bytes.fromhex(value) for value in case["chunks"].split(",")]
    assert head.play_screen_animation(chunks) == case["expect_data"]
    prompt_continue("请人工确认屏幕动画显示。")
