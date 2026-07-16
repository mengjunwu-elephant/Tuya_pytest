# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'upper_power_off')

@allure.feature('UpperBody')
@allure.story('upper_power_off')
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_upper_power_off(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 is_upper_powered_on 接口'):
        original = upper_body.is_upper_powered_on()
        logger.debug('接口 is_upper_powered_on 返回：%r', original)
    assert isinstance(original, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(original).__name__}: {original!r}'
    assert len(original) == 2, f'返回长度错误，期望 {2}，实际为 {len(original)}'
    try:
        with allure.step('调用 upper_power_off 接口'):
            upper_body.upper_power_off()
        with allure.step('调用 is_upper_powered_on 接口'):
            states = upper_body.is_upper_powered_on()
            logger.debug('接口 is_upper_powered_on 返回：%r', states)
        assert isinstance(states, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(states).__name__}: {states!r}'
        assert len(states) == 2, f'返回长度错误，期望 {2}，实际为 {len(states)}'
        assert all((state == case['expect_data'] for state in states))
    finally:
        if any((state == 1 for state in original)):
            with allure.step('调用 upper_power_on 接口'):
                upper_body.upper_power_on()
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
