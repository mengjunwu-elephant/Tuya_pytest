# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_upper_model_direction')

@allure.feature('UpperBody')
@allure.story('set_upper_model_direction')
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_upper_model_direction(upper_body, left_arm, right_arm, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    joint_id = case['joint_id']
    with allure.step('调用 get_upper_model_direction 接口'):
        original = upper_body.get_upper_model_direction()
        logger.debug('接口 get_upper_model_direction 返回：%r', original)
    assert isinstance(original, dict), f'返回类型错误，期望 dict，实际为 {type(original).__name__}'
    assert 'left' in original and 'right' in original, f'返回结果缺少 left/right: {original!r}'
    assert isinstance(original['left'], (list, tuple)) and isinstance(original['right'], (list, tuple))
    assert len(original['left']) == 7 and len(original['right']) == 7, f"左右臂数据长度应为 {7}，实际为 {len(original['left'])}/{len(original['right'])}"
    try:
        with allure.step('调用 set_upper_model_direction 接口'):
            upper_body.set_upper_model_direction(joint_id, case['direction'])
        with allure.step('调用 get_upper_model_direction 接口'):
            actual = upper_body.get_upper_model_direction()
            logger.debug('接口 get_upper_model_direction 返回：%r', actual)
        assert isinstance(actual, dict), f'返回类型错误，期望 dict，实际为 {type(actual).__name__}'
        assert 'left' in actual and 'right' in actual, f'返回结果缺少 left/right: {actual!r}'
        assert isinstance(actual['left'], (list, tuple)) and isinstance(actual['right'], (list, tuple))
        assert len(actual['left']) == 7 and len(actual['right']) == 7, f"左右臂数据长度应为 {7}，实际为 {len(actual['left'])}/{len(actual['right'])}"
        assert actual['left'][joint_id - 1] == case['expect_data']
        assert actual['right'][joint_id - 1] == case['expect_data']
    finally:
        with allure.step('调用 set_upper_model_direction 接口'):
            left_arm.set_upper_model_direction(joint_id, original['left'][joint_id - 1])
        with allure.step('调用 set_upper_model_direction 接口'):
            right_arm.set_upper_model_direction(joint_id, original['right'][joint_id - 1])
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
