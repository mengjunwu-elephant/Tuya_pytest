# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from common1.operator_input import prompt_continue
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "set_head_joint_enable")

@allure.feature("头部 PI4")
@allure.story("设置关节使能")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_head_joint_enable(head, case):
    prompt_continue("请确认使能恢复参数正确后继续。")
    assert case["restore_value"] in (0, 1), "Excel 必须提供使能恢复状态"
    try:
        assert head.set_head_joint_enable(case["joint_id"], case["state"]) == case["expect_data"]
    finally:
        head.set_head_joint_enable(case["joint_id"], case["restore_value"])
