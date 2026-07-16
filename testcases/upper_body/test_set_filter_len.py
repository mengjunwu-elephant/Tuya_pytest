# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_filter_len')

@allure.feature('UpperBody')
@allure.story('set_filter_len')
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_filter_len(left_arm, right_arm, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    target = left_arm if case['arm'] == 'left' else right_arm
    with allure.step('调用 get_upper_filter_len 接口'):
        original = target.get_upper_filter_len()
        logger.debug('接口 get_upper_filter_len 返回：%r', original)
    assert isinstance(original, int) and (not isinstance(original, bool)), f'返回类型错误，期望 int，实际为 {type(original).__name__}: {original!r}'
    try:
        with allure.step('调用 set_filter_len 接口'):
            target.set_filter_len(case['length'])
        with allure.step('调用 get_upper_filter_len 接口'):
            actual = target.get_upper_filter_len()
            logger.debug('接口 get_upper_filter_len 返回：%r', actual)
        assert isinstance(actual, int) and not isinstance(actual, bool)
        assert actual == case['expect_data']
    finally:
        with allure.step('调用 set_filter_len 接口'):
            target.set_filter_len(original)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
