# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from common1.operator_input import prompt_continue
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "head_power_on")

@allure.feature("头部 PI4")
@allure.story("头部上电")
@pytest.mark.head
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_head_power_on(head, case):
    original = head.is_head_powered_on()
    try:
        assert head.head_power_on() == case["expect_data"]
        assert head.is_head_powered_on() == 1
    finally:
        (head.head_power_on if original else head.head_power_off)()
