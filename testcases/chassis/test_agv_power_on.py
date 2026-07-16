# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'agv_power_on')

@allure.feature('Chassis')
@allure.story('agv_power_on')
@pytest.mark.chassis
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_agv_power_on(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 agv_power_on 接口'):
        response_1 = chassis.agv_power_on()
        logger.debug('接口 agv_power_on 返回：%r', response_1)
    assert isinstance(response_1, int) and (not isinstance(response_1, bool)) and (response_1 == 0) or (isinstance(response_1, dict) and 'status' in response_1 and ('message' in response_1)), f'底盘电源状态格式错误: {response_1!r}'
    with allure.step('调用 is_agv_powered_on 接口'):
        response_2 = chassis.is_agv_powered_on()
        logger.debug('接口 is_agv_powered_on 返回：%r', response_2)
    assert isinstance(response_2, int) and (not isinstance(response_2, bool)) and (response_2 == 0) or (isinstance(response_2, dict) and 'status' in response_2 and ('message' in response_2)), f'底盘电源状态格式错误: {response_2!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
