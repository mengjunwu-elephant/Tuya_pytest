# -*- coding: utf-8 -*-
import allure
import pytest
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_upper_joint_enable')

@allure.feature('UpperBody')
@allure.story('set_upper_joint_enable')
@pytest.mark.upper_body
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_upper_joint_enable(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    prompt_continue(case['manual_check'], title='关节失能安全确认')
    try:
        with allure.step('调用 set_upper_joint_enable 接口'):
            response = upper_body.set_upper_joint_enable(case['joint_id'], case['state'])
            logger.debug('接口 set_upper_joint_enable 返回：%r', response)
        assert response is not None, '关节使能接口未返回 ACK'
    finally:
        with allure.step('调用 set_upper_joint_enable 接口'):
            upper_body.set_upper_joint_enable(case['joint_id'], 1)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
