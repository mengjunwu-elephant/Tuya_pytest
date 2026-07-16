# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_head_main_version')

@allure.feature('TuyaRobot 头部')
@allure.story('获取头部主版本')
@pytest.mark.head
@pytest.mark.smoke
@pytest.mark.parametrize('case', [case for case in cases if case['test_type'] == 'normal'], ids=lambda case: case['title'])
def test_get_head_main_version(head, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_head_main_version 接口'):
        response = head.get_head_main_version()
        logger.debug('接口 get_head_main_version 返回：%r', response)
    assert isinstance(response, (int, float))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
