# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_wheel_brake')

@allure.feature('Chassis')
@allure.story('set_agv_wheel_brake')
@pytest.mark.chassis
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_agv_wheel_brake(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    with allure.step('调用 get_agv_wheel_brake 接口'):
        original = chassis.get_agv_wheel_brake()
        logger.debug('接口 get_agv_wheel_brake 返回：%r', original)
    assert isinstance(original, int) and (not isinstance(original, bool))
    assert original in (0, 1), f'期望 0/1，实际为 {original!r}'
    try:
        with allure.step('调用 set_agv_wheel_brake 接口'):
            chassis.set_agv_wheel_brake(case['state'])
        with allure.step('调用 get_agv_wheel_brake 接口'):
            actual = chassis.get_agv_wheel_brake()
            logger.debug('接口 get_agv_wheel_brake 返回：%r', actual)
        assert isinstance(actual, int) and not isinstance(actual, bool)
        assert actual in (0, 1)
        assert actual == case['expect_data']
    finally:
        with allure.step('调用 set_agv_wheel_brake 接口'):
            chassis.set_agv_wheel_brake(original)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
