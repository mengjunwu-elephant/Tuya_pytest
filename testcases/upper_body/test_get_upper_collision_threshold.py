# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_collision_threshold')

@allure.feature('UpperBody')
@allure.story('get_upper_collision_threshold')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_collision_threshold(left_arm, right_arm, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    target = left_arm if case['arm'] == 'left' else right_arm
    with allure.step('调用 get_upper_collision_threshold 接口'):
        value = target.get_upper_collision_threshold()
        logger.debug('接口 get_upper_collision_threshold 返回：%r', value)
    assert isinstance(value, int) and (not isinstance(value, bool)), f'返回类型错误，期望 int，实际为 {type(value).__name__}: {value!r}'
    assert 0 <= value <= 255
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
