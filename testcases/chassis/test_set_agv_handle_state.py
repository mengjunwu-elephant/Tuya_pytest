# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_handle_state')

@allure.feature('底盘')
@allure.story('底盘接口验证：set_agv_handle_state')
@pytest.mark.chassis
@pytest.mark.reset
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_agv_handle_state(chassis, case):
    title = case['title']
    expected = case["expect_data"]
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'state:{case["state"]}')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    with allure.step('调用 get_agv_handle_state 接口'):
        original = chassis.get_agv_handle_state()
        logger.debug(f"接口 get_agv_handle_state 返回：{original}")
    with allure.step("断言接口返回结果"):
        assert isinstance(original, int) and (not isinstance(original, bool))
    with allure.step("断言接口返回结果"):
        assert original in (0, 1), f'期望 0/1，实际为 {original!r}'
    try:
        with allure.step('调用 set_agv_handle_state 接口'):
            chassis.set_agv_handle_state(case['state'])
        with allure.step('调用 get_agv_handle_state 接口'):
            actual = chassis.get_agv_handle_state()
            logger.debug(f"接口 get_agv_handle_state 返回：{actual}")
        with allure.step("断言接口返回结果"):
            assert isinstance(actual, int) and not isinstance(actual, bool)
        with allure.step("断言接口返回结果"):
            assert actual in (0, 1)
        with allure.step("断言接口返回结果"):
            allure.attach(str(expected), name="期望值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
    finally:
        with allure.step('调用 set_agv_handle_state 接口'):
            chassis.set_agv_handle_state(original)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
