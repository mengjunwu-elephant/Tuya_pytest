# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from common1.operator_input import prompt_continue
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "clear_head_error")

@allure.feature("头部 PI4")
@allure.story("清除头部错误")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_clear_head_error(head, case):
    prompt_continue("请确认错误原因已经排除后继续清错。")
    assert head.clear_head_error(case["joint_id"]) == case["expect_data"]
