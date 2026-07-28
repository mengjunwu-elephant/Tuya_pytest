# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_lift_calibrate')

@allure.feature('Chassis')
@allure.story('set_agv_lift_calibrate')
@pytest.mark.chassis
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_agv_lift_calibrate(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'manual_check:{case["manual_check"]}')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    prompt_continue(case['manual_check'], title='底盘升降标定确认')
    with allure.step('调用 set_agv_lift_calibrate 接口'):
        chassis.set_agv_lift_calibrate()
    with allure.step('调用 is_agv_lift_init_calibrate 接口'):
        actual = chassis.is_agv_lift_init_calibrate()
        logger.debug(f"接口 is_agv_lift_init_calibrate 返回：{actual}")
    with allure.step("断言接口返回结果"):
        assert isinstance(actual, bool)
    with allure.step("断言接口返回结果"):
        assert actual is True
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
