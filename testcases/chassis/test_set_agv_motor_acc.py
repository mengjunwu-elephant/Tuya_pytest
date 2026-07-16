# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_motor_acc')

@allure.feature('Chassis')
@allure.story('set_agv_motor_acc')
@pytest.mark.chassis
@pytest.mark.reset
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_agv_motor_acc(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    device_id = case['device_id']
    with allure.step('调用 get_agv_motor_acc 接口'):
        original = chassis.get_agv_motor_acc(device_id)
        logger.debug('接口 get_agv_motor_acc 返回：%r', original)
    assert isinstance(original, int) and (not isinstance(original, bool)), f'返回类型错误，期望 int，实际为 {type(original).__name__}: {original!r}'
    try:
        with allure.step('调用 set_agv_motor_acc 接口'):
            chassis.set_agv_motor_acc(device_id, case['acc'])
        with allure.step('调用 get_agv_motor_acc 接口'):
            actual = chassis.get_agv_motor_acc(device_id)
            logger.debug('接口 get_agv_motor_acc 返回：%r', actual)
        assert isinstance(actual, int) and (not isinstance(actual, bool)), f'返回类型错误，期望 int，实际为 {type(actual).__name__}: {actual!r}'
        assert actual == case['expect_data']
    finally:
        with allure.step('调用 set_agv_motor_acc 接口'):
            chassis.set_agv_motor_acc(device_id, original)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
