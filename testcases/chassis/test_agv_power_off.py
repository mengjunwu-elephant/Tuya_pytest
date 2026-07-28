# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'agv_power_off')

@allure.feature('底盘')
@allure.story('底盘接口验证：agv_power_off')
@pytest.mark.chassis
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_agv_power_off(device, chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('读取底盘原始上电状态'):
        original_status = TuyaRobotBase.result_data(chassis.is_agv_powered_on())
        was_powered_on = original_status == 0
    try:
        if not was_powered_on:
            with allure.step('恢复前置：先使底盘上电'):
                power_on_response = chassis.agv_power_on()
                assert TuyaRobotBase.result_data(power_on_response) == 0, f'底盘上电接口业务返回错误: {power_on_response!r}'
                device.wait_chassis_power(expected_on=True)
        with allure.step('调用 agv_power_off 接口'):
            response = chassis.agv_power_off()
            logger.debug(f"接口 agv_power_off 返回：{response}")
        with allure.step("断言接口返回结果"):
            assert TuyaRobotBase.result_data(response) == 1, f'底盘下电接口业务返回错误: {response!r}'
            device.wait_chassis_power(expected_on=False)
    finally:
        if was_powered_on:
            with allure.step('恢复底盘原始上电状态'):
                restore_response = chassis.agv_power_on()
                assert TuyaRobotBase.result_data(restore_response) == 0, f'底盘上电恢复失败: {restore_response!r}'
                device.wait_chassis_power(expected_on=True)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
