# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_wheel_enabled')

@allure.feature('Chassis')
@allure.story('set_agv_wheel_enabled')
@pytest.mark.chassis
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_agv_wheel_enabled(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    try:
        with allure.step('调用 set_agv_wheel_enabled 接口'):
            response = chassis.set_agv_wheel_enabled(case['device_id'], case['state'])
            logger.debug('接口 set_agv_wheel_enabled 返回：%r', response)
        assert response is not None, '轮毂使能接口未返回 ACK'
    finally:
        with allure.step('调用 set_agv_wheel_enabled 接口'):
            chassis.set_agv_wheel_enabled(case['device_id'], 1)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
