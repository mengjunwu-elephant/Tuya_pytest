# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "play_screen_animation")

@allure.feature("头部 PI4")
@allure.story("发送屏幕动画")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_play_screen_animation(head, case):
    if not case["chunks"]:
        pytest.skip("Excel 未提供批准的 bytes 动画数据")
    chunks = [bytes.fromhex(value) for value in case["chunks"].split(",")]
    assert head.play_screen_animation(chunks) == case["expect_data"]
    prompt_continue("请人工确认屏幕动画显示。")
