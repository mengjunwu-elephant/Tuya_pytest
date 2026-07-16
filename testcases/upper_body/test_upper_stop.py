# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'upper_stop')

@allure.feature('UpperBody')
@allure.story('upper_stop')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_upper_stop(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    with allure.step('调用 upper_stop 接口'):
        upper_body.upper_stop()
    with allure.step('调用 get_upper_is_moving 接口'):
        states = upper_body.get_upper_is_moving()
        logger.debug('接口 get_upper_is_moving 返回：%r', states)
    assert isinstance(states, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(states).__name__}: {states!r}'
    assert len(states) == 2, f'返回长度错误，期望 {2}，实际为 {len(states)}'
    assert all((state == case['expect_data'] for state in states))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
