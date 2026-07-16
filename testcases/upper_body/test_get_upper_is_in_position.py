# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_is_in_position')

@allure.feature('UpperBody')
@allure.story('get_upper_is_in_position')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_is_in_position(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    with allure.step('调用 get_upper_angles 接口'):
        current = upper_body.get_upper_angles()
        logger.debug('接口 get_upper_angles 返回：%r', current)
    assert isinstance(current, dict), f'返回类型错误，期望 dict，实际为 {type(current).__name__}'
    assert 'left' in current and 'right' in current, f'返回结果缺少 left/right: {current!r}'
    assert isinstance(current['left'], (list, tuple)) and isinstance(current['right'], (list, tuple))
    assert len(current['left']) == 8 and len(current['right']) == 8, f"左右臂数据长度应为 {8}，实际为 {len(current['left'])}/{len(current['right'])}"
    with allure.step('调用 get_upper_is_in_position 接口'):
        state = upper_body.get_upper_is_in_position(case['mode'], left=current['left'], right=current['right'])
        logger.debug('接口 get_upper_is_in_position 返回：%r', state)
    assert isinstance(state, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(state).__name__}: {state!r}'
    assert len(state) == 2, f'返回长度错误，期望 {2}，实际为 {len(state)}'
    assert all((value in (0, 1) for value in state))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
