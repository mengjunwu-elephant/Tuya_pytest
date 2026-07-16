# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_gripper_param')

@allure.feature('UpperBody')
@allure.story('get_upper_gripper_param')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_gripper_param(left_arm, right_arm, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    target = left_arm if case['arm'] == 'left' else right_arm
    with allure.step('调用 get_upper_gripper_param 接口'):
        response = target.get_upper_gripper_param()
        logger.debug('接口 get_upper_gripper_param 返回：%r', response)
    assert response is not None
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
