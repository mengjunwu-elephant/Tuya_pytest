# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_upper_collision_mode')

@allure.feature('UpperBody')
@allure.story('set_upper_collision_mode')
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_set_upper_collision_mode(left_arm, right_arm, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    target = left_arm if case['arm'] == 'left' else right_arm
    with allure.step('调用 get_upper_collision_mode 接口'):
        original = target.get_upper_collision_mode()
        logger.debug('接口 get_upper_collision_mode 返回：%r', original)
    assert isinstance(original, int) and (not isinstance(original, bool)), f'返回类型错误，期望 int，实际为 {type(original).__name__}: {original!r}'
    try:
        with allure.step('调用 set_upper_collision_mode 接口'):
            target.set_upper_collision_mode(case['mode'])
        with allure.step('调用 get_upper_collision_mode 接口'):
            actual = target.get_upper_collision_mode()
            logger.debug('接口 get_upper_collision_mode 返回：%r', actual)
        assert isinstance(actual, int) and not isinstance(actual, bool)
        assert 0 <= actual <= 255
        assert actual == case['expect_data']
    finally:
        with allure.step('调用 set_upper_collision_mode 接口'):
            target.set_upper_collision_mode(original)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
