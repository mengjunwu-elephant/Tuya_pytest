# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation.errors import TuyaRobotDualArmDataException
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_upper_fresh_mode')
normal_cases = [case for case in cases if case['test_type'] == 'normal']
exception_cases = [case for case in cases if case['test_type'] == 'exception']

@allure.feature('UpperBody')
@allure.story('set_upper_fresh_mode')
@pytest.mark.upper_body
@pytest.mark.reset
@pytest.mark.parametrize('case', normal_cases, ids=lambda case: case['title'])
def test_set_upper_fresh_mode(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    with allure.step('读取测试前的刷新模式'):
        original_response = upper_body.get_upper_fresh_mode()
        logger.debug('原始刷新模式：%r', original_response)
    assert isinstance(original_response, (list, tuple))
    assert len(original_response) == 2
    original = list(original_response)
    try:
        with allure.step('调用 set_upper_fresh_mode 接口'):
            upper_body.set_upper_fresh_mode(case['state'])
        with allure.step('调用 get_upper_fresh_mode 接口'):
            actual = upper_body.get_upper_fresh_mode()
            logger.debug('接口 get_upper_fresh_mode 返回：%r', actual)
        assert isinstance(actual, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(actual).__name__}: {actual!r}'
        assert len(actual) == 2, f'返回长度错误，期望 {2}，实际为 {len(actual)}'
        assert list(actual) == [case['expect_data'], case['expect_data']]
    finally:
        with allure.step('调用 set_upper_fresh_mode 接口'):
            upper_body.left_arm.set_upper_fresh_mode(original[0])
        with allure.step('调用 set_upper_fresh_mode 接口'):
            upper_body.right_arm.set_upper_fresh_mode(original[1])
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')

@allure.feature('UpperBody')
@allure.story('set_upper_fresh_mode')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', exception_cases, ids=lambda case: case['title'])
def test_set_upper_fresh_mode_exception(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with pytest.raises(TuyaRobotDualArmDataException):
        with allure.step('调用 set_upper_fresh_mode 接口'):
            upper_body.set_upper_fresh_mode(case['state'])
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
