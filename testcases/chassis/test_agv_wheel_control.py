# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
import time

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'agv_wheel_control')

@allure.feature('Chassis')
@allure.story('agv_wheel_control')
@pytest.mark.chassis
@pytest.mark.motion
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_agv_wheel_control(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'duration:{case["duration"]}')
    logger.debug(f'forward_mps:{case["forward_mps"]}')
    logger.debug(f'rotate_rads:{case["rotate_rads"]}')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    try:
        with allure.step('调用 agv_wheel_control 接口'):
            response = chassis.agv_wheel_control(case['forward_mps'], case['rotate_rads'])
            logger.debug(f"接口 agv_wheel_control 返回：{response}")
        with allure.step("断言接口返回结果"):
            assert response is not None, '轮毂控制接口未返回 ACK'
        time.sleep(case['duration'])
    finally:
        with allure.step('调用 agv_wheel_stop 接口'):
            chassis.agv_wheel_stop()
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
