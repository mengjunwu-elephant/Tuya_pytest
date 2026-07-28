# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'clear_agv_error')

@allure.feature('底盘')
@allure.story('底盘接口验证：clear_agv_error')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_clear_agv_error(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'device_id:{case["device_id"]}')
    with allure.step('调用 clear_agv_error 接口'):
        response = chassis.clear_agv_error(case['device_id'])
        logger.debug(f"接口 clear_agv_error 返回：{response}")
    with allure.step("断言接口返回结果"):
        assert TuyaRobotBase.result_data(response) == 1, f'底盘清错接口业务返回错误: {response!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
