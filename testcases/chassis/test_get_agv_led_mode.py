# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_led_mode')

@allure.feature('Chassis')
@allure.story('get_agv_led_mode')
@pytest.mark.chassis
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_agv_led_mode(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_agv_led_mode 接口'):
        response_1 = chassis.get_agv_led_mode()
        logger.debug('接口 get_agv_led_mode 返回：%r', response_1)
    assert isinstance(response_1, int) and (not isinstance(response_1, bool))
    assert response_1 in (0, 1), f'期望 0/1，实际为 {response_1!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
