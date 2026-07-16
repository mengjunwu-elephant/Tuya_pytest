# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'upper_solve_inv_kinematics')

@allure.feature('UpperBody')
@allure.story('upper_solve_inv_kinematics')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_upper_solve_inv_kinematics(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    with allure.step('调用 get_upper_coords 接口'):
        current = upper_body.get_upper_coords()
        logger.debug('接口 get_upper_coords 返回：%r', current)
    assert isinstance(current, dict), f'返回类型错误，期望 dict，实际为 {type(current).__name__}'
    assert 'left' in current and 'right' in current, f'返回结果缺少 left/right: {current!r}'
    assert isinstance(current['left'], (list, tuple)) and isinstance(current['right'], (list, tuple))
    assert len(current['left']) == 6 and len(current['right']) == 6, f"左右臂数据长度应为 {6}，实际为 {len(current['left'])}/{len(current['right'])}"
    with allure.step('调用 upper_solve_inv_kinematics 接口'):
        result = upper_body.upper_solve_inv_kinematics(current['left'], current['right'])
        logger.debug('接口 upper_solve_inv_kinematics 返回：%r', result)
    assert result is not None
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
