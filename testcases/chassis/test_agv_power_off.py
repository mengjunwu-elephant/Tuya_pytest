# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'agv_power_off')

@allure.feature('Chassis')
@allure.story('agv_power_off')
@pytest.mark.chassis
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_agv_power_off(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    try:
        with allure.step('调用 agv_power_off 接口'):
            response = chassis.agv_power_off()
            logger.debug(f"接口 agv_power_off 返回：{response}")
        with allure.step("断言接口返回结果"):
            assert response is not None, '底盘下电接口未返回 ACK'
    finally:
        with allure.step('调用 agv_power_on 接口'):
            chassis.agv_power_on()
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
