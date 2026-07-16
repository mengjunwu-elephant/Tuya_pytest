# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'is_agv_powered_on')

@allure.feature('Chassis')
@allure.story('is_agv_powered_on')
@pytest.mark.chassis
@pytest.mark.smoke
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_is_agv_powered_on(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 is_agv_powered_on 接口'):
        response_1 = chassis.is_agv_powered_on()
        logger.debug('接口 is_agv_powered_on 返回：%r', response_1)
    assert isinstance(response_1, int) and (not isinstance(response_1, bool)) and (response_1 == 0) or (isinstance(response_1, dict) and 'status' in response_1 and ('message' in response_1)), f'底盘电源状态格式错误: {response_1!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
