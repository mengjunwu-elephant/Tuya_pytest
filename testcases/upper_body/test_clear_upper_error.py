# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'clear_upper_error')

@allure.feature('UpperBody')
@allure.story('clear_upper_error')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_clear_upper_error(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 clear_upper_error 接口'):
        response = upper_body.clear_upper_error(case['joint_id'])
        logger.debug('接口 clear_upper_error 返回：%r', response)
    assert response is not None, '上半身清错接口未返回 ACK'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
