# -*- coding: utf-8 -*-
import time
import allure
import pytest
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'upper_drag_teach_record_pause')

@allure.feature('UpperBody')
@allure.story('upper_drag_teach_record_pause')
@pytest.mark.upper_body
@pytest.mark.manual
@pytest.mark.motion
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_upper_drag_teach_record_pause(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    prompt_continue(case['manual_check'], title='拖动示教暂停')
    try:
        with allure.step('调用 upper_drag_teach_record 接口'):
            record_response = upper_body.upper_drag_teach_record()
            logger.debug('接口 upper_drag_teach_record 返回：%r', record_response)
        assert record_response is not None, '拖动示教录制接口未返回 ACK'
        time.sleep(case['duration'])
    finally:
        with allure.step('调用 upper_drag_teach_record_pause 接口'):
            pause_response = upper_body.upper_drag_teach_record_pause()
            logger.debug('接口 upper_drag_teach_record_pause 返回：%r', pause_response)
        assert pause_response is not None, '拖动示教暂停接口未返回 ACK'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
