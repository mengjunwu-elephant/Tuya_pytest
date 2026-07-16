# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_model_direction')

@allure.feature('UpperBody')
@allure.story('get_upper_model_direction')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_model_direction(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_upper_model_direction 接口'):
        values = upper_body.get_upper_model_direction()
        logger.debug('接口 get_upper_model_direction 返回：%r', values)
    assert isinstance(values, dict), f'返回类型错误，期望 dict，实际为 {type(values).__name__}: {values!r}'
    response_1 = values['left']
    assert isinstance(response_1, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(response_1).__name__}: {response_1!r}'
    response_2 = values['right']
    assert isinstance(response_2, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(response_2).__name__}: {response_2!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
