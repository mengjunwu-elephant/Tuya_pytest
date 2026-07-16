# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'upper_drag_teach_record_clear')

@allure.feature('UpperBody')
@allure.story('upper_drag_teach_record_clear')
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_upper_drag_teach_record_clear(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('检查上半身上电状态'):
        power_state = upper_body.is_upper_powered_on()
        assert isinstance(power_state, (list, tuple)), f'上电状态类型错误: {power_state!r}'
        assert len(power_state) == 2, f'上电状态长度错误: {power_state!r}'
        if list(power_state) != [1, 1]:
            pytest.skip(f'上半身未完成双臂上电: {power_state!r}')
    with allure.step('调用 upper_drag_teach_record_clear 接口'):
        response = upper_body.upper_drag_teach_record_clear()
        logger.debug('接口 upper_drag_teach_record_clear 返回：%r', response)
    assert response is not None, '清空拖动示教轨迹接口未返回 ACK'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
