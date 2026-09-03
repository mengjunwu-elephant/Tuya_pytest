# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "is_head_in_position")

@allure.feature("头部 PI4")
@allure.story("读取关节到位状态")
@pytest.mark.head
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_is_head_in_position(head, case):
    actual = head.is_head_in_position(case["joint_id"], case["angle"])
    assert actual in (0, 1)
