# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from common1.operator_input import prompt_continue
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "set_head_debug_state")

@allure.feature("头部 PI4")
@allure.story("设置调试状态")
@pytest.mark.head
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_head_debug_state(head, case):
    original = head.get_head_debug_state()
    try:
        assert head.set_head_debug_state(case["state"]) == case["expect_data"]
        assert head.get_head_debug_state() == case["state"]
    finally:
        head.set_head_debug_state(original)
        assert head.get_head_debug_state() == original
