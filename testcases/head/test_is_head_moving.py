# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "is_head_moving")

@allure.feature("头部 PI4")
@allure.story("is_head_moving")
@pytest.mark.head
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_is_head_moving(head, case):
    logger.info("》》》》》用例【%s】开始测试《《《《《", case["title"])
    logger.debug("test_api:%s", case["api"])
    with allure.step("调用 is_head_moving 接口"):
        actual = head.is_head_moving()
    with allure.step("断言接口返回"):
        assert actual in (0, 1)
    logger.info("✅ 用例【%s】测试通过", case["title"])
    logger.info("》》》》》用例【%s】测试完成《《《《《", case["title"])
