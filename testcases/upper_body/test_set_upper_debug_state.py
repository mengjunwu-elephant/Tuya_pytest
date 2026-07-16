# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation.errors import TuyaRobotDualArmDataException
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_upper_debug_state')
normal_cases = [case for case in cases if case['test_type'] == 'normal']
exception_cases = [case for case in cases if case['test_type'] == 'exception']

@allure.feature('UpperBody')
@allure.story('set_upper_debug_state')
@pytest.mark.upper_body
@pytest.mark.reset
@pytest.mark.parametrize('case', normal_cases, ids=lambda case: case['title'])
def test_set_upper_debug_state(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    with allure.step('调用 get_upper_debug_state 接口'):
        original = upper_body.get_upper_debug_state()
        logger.debug('接口 get_upper_debug_state 返回：%r', original)
    assert isinstance(original, int) and (not isinstance(original, bool)), f'返回类型错误，期望 int，实际为 {type(original).__name__}: {original!r}'
    try:
        with allure.step('调用 set_upper_debug_state 接口'):
            upper_body.set_upper_debug_state(case['state'])
        with allure.step('调用 get_upper_debug_state 接口'):
            actual = upper_body.get_upper_debug_state()
            logger.debug('接口 get_upper_debug_state 返回：%r', actual)
        assert isinstance(actual, int) and (not isinstance(actual, bool)), f'返回类型错误，期望 int，实际为 {type(actual).__name__}: {actual!r}'
        assert actual == case['expect_data']
    finally:
        with allure.step('调用 set_upper_debug_state 接口'):
            upper_body.set_upper_debug_state(original)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')

@allure.feature('UpperBody')
@allure.story('set_upper_debug_state')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', exception_cases, ids=lambda case: case['title'])
def test_set_upper_debug_state_exception(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with pytest.raises(TuyaRobotDualArmDataException):
        with allure.step('调用 set_upper_debug_state 接口'):
            upper_body.set_upper_debug_state(case['state'])
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
