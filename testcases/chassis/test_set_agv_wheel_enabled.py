# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_wheel_enabled')

@allure.feature('底盘')
@allure.story('底盘接口验证：set_agv_wheel_enabled')
@pytest.mark.chassis
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_agv_wheel_enabled(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'device_id:{case["device_id"]}')
    logger.debug(f'state:{case["state"]}')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    prompt_continue('确认允许本用例结束后将轮毂保持为使能状态。', title='轮毂使能状态确认')
    try:
        with allure.step('调用 set_agv_wheel_enabled 接口'):
            response = chassis.set_agv_wheel_enabled(case['device_id'], case['state'])
            logger.debug(f"接口 set_agv_wheel_enabled 返回：{response}")
        with allure.step("断言接口返回结果"):
            assert TuyaRobotBase.result_data(response) == 1, f'轮毂使能接口业务返回错误: {response!r}'
    finally:
        with allure.step('调用 set_agv_wheel_enabled 接口'):
            restore_response = chassis.set_agv_wheel_enabled(case['device_id'], 1)
            assert TuyaRobotBase.result_data(restore_response) == 1, f'轮毂使能恢复失败: {restore_response!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
