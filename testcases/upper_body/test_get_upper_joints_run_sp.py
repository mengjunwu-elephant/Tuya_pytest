# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_joints_run_sp')

@allure.feature('UpperBody')
@allure.story('get_upper_joints_run_sp')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_joints_run_sp(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_upper_joints_run_sp 接口'):
        response_1 = upper_body.get_upper_joints_run_sp()
        logger.debug('接口 get_upper_joints_run_sp 返回：%r', response_1)
    assert isinstance(response_1, dict), f'返回类型错误，期望 dict，实际为 {type(response_1).__name__}'
    assert 'left' in response_1 and 'right' in response_1, f'返回结果缺少 left/right: {response_1!r}'
    assert isinstance(response_1['left'], (list, tuple)) and isinstance(response_1['right'], (list, tuple))
    assert len(response_1['left']) == 8 and len(response_1['right']) == 8, f"左右臂数据长度应为 {8}，实际为 {len(response_1['left'])}/{len(response_1['right'])}"
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
