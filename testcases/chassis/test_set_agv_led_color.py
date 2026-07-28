# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_led_color')

@allure.feature('Chassis')
@allure.story('set_agv_led_color')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_agv_led_color(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'b:{case["b"]}')
    logger.debug(f'brightness:{case["brightness"]}')
    logger.debug(f'g:{case["g"]}')
    logger.debug(f'r:{case["r"]}')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    try:
        with allure.step('调用 set_agv_led_color 接口'):
            response = chassis.set_agv_led_color(case['r'], case['g'], case['b'], case['brightness'])
            logger.debug(f"接口 set_agv_led_color 返回：{response}")
        with allure.step("断言接口返回结果"):
            assert response is not None, 'LED 颜色设置接口未返回 ACK'
    finally:
        with allure.step('调用 set_agv_led_color 接口'):
            chassis.set_agv_led_color(0, 255, 0, case['brightness'])
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
