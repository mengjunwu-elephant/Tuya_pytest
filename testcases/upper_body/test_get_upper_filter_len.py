# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_filter_len')

@allure.feature('UpperBody')
@allure.story('get_upper_filter_len')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_filter_len(left_arm, right_arm, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    target = left_arm if case['arm'] == 'left' else right_arm
    with allure.step('调用 get_upper_filter_len 接口'):
        response_1 = target.get_upper_filter_len()
        logger.debug('接口 get_upper_filter_len 返回：%r', response_1)
    assert isinstance(response_1, int) and (not isinstance(response_1, bool)), f'返回类型错误，期望 int，实际为 {type(response_1).__name__}: {response_1!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
