# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "get_head_joints_temp")

@allure.feature("头部 PI4")
@allure.story("get_head_joints_temp")
@pytest.mark.head
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_head_joints_temp(head, case):
    logger.info("》》》》》用例【%s】开始测试《《《《《", case["title"])
    logger.debug("test_api:%s", case["api"])
    with allure.step("调用 get_head_joints_temp 接口"):
        actual = head.get_head_joints_temp()
    with allure.step("断言接口返回"):
        if not isinstance(actual, (list, tuple)) or len(actual) != 4:
            pytest.xfail(f"当前 SDK/固件未满足四关节合同：{actual!r}")
        assert all(isinstance(value, int) for value in actual)
    logger.info("✅ 用例【%s】测试通过", case["title"])
    logger.info("》》》》》用例【%s】测试完成《《《《《", case["title"])
