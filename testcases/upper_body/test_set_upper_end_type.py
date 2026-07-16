# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_upper_end_type')

@allure.feature('UpperBody')
@allure.story('set_upper_end_type')
@pytest.mark.upper_body
@pytest.mark.reset
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_upper_end_type(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    with allure.step('调用 get_upper_end_type 接口'):
        original = upper_body.get_upper_end_type()
        logger.debug('接口 get_upper_end_type 返回：%r', original)
    assert isinstance(original, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(original).__name__}: {original!r}'
    assert len(original) == 2, f'返回长度错误，期望 {2}，实际为 {len(original)}'
    try:
        with allure.step('调用 set_upper_end_type 接口'):
            upper_body.set_upper_end_type(case['end_type'])
        with allure.step('调用 get_upper_end_type 接口'):
            actual = upper_body.get_upper_end_type()
            logger.debug('接口 get_upper_end_type 返回：%r', actual)
        assert isinstance(actual, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(actual).__name__}: {actual!r}'
        assert len(actual) == 2, f'返回长度错误，期望 {2}，实际为 {len(actual)}'
        assert actual == [case['expect_data'], case['expect_data']]
    finally:
        with allure.step('调用 set_upper_end_type 接口'):
            upper_body.set_upper_end_type(left=original[0], right=original[1])
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
