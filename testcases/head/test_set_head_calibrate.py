# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from common1.operator_input import prompt_continue
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "set_head_calibrate")

@allure.feature("头部 PI4")
@allure.story("校准头部关节")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_head_calibrate(head, case):
    prompt_continue("请确认已获得校准授权且关节位于机械刻度位置。")
    assert head.set_head_calibrate(case["joint_id"]) == case["expect_data"]
    prompt_continue("请人工确认校准后的零位和错误状态。")
