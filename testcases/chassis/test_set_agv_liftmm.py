# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'set_agv_liftmm')

@allure.feature('底盘')
@allure.story('底盘接口验证：set_agv_liftmm')
@pytest.mark.chassis
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_agv_liftmm(chassis, case):
    title = case['title']
    expected = case["expect_data"]
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'lift_mm:{case["lift_mm"]}')
    logger.debug(f'speed:{case["speed"]}')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    prompt_continue('确认升降机构周边无人、无障碍物，且急停可用。', title='底盘升降运动确认')
    with allure.step('调用 get_agv_liftmm 接口'):
        original = chassis.get_agv_liftmm()
        logger.debug(f"接口 get_agv_liftmm 返回：{original}")
    with allure.step("断言接口返回结果"):
        assert isinstance(original, int) and (not isinstance(original, bool)), f'返回类型错误，期望 int，实际为 {type(original).__name__}: {original!r}'
    try:
        with allure.step('调用 set_agv_liftmm 接口'):
            chassis.set_agv_liftmm(case['lift_mm'], case['speed'])
        with allure.step('调用 get_agv_liftmm 接口'):
            actual = chassis.get_agv_liftmm()
            logger.debug(f"接口 get_agv_liftmm 返回：{actual}")
        with allure.step("断言接口返回结果"):
            assert isinstance(actual, int) and (not isinstance(actual, bool)), f'返回类型错误，期望 int，实际为 {type(actual).__name__}: {actual!r}'
        with allure.step("断言接口返回结果"):
            allure.attach(str(expected), name="期望值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际值", attachment_type=allure.attachment_type.TEXT)
            assert abs(actual - expected) <= case['tolerance']
    finally:
        with allure.step('调用 set_agv_liftmm 接口'):
            chassis.set_agv_liftmm(original, case['speed'])
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
