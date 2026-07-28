# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_auto_report')

@allure.feature('底盘')
@allure.story('底盘接口验证：get_agv_auto_report')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_agv_auto_report(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('调用 get_agv_auto_report 接口'):
        response_1 = chassis.get_agv_auto_report()
        logger.debug(f"接口 get_agv_auto_report 返回：{response_1}")
    with allure.step("断言接口返回结果"):
        assert isinstance(response_1, int) and (not isinstance(response_1, bool))
    with allure.step("断言接口返回结果"):
        assert response_1 in (0, 1), f'期望 0/1，实际为 {response_1!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
