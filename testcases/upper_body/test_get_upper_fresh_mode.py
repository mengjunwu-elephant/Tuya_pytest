# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_fresh_mode')

@allure.feature('UpperBody')
@allure.story('get_upper_fresh_mode')
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_fresh_mode(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('调用 get_upper_fresh_mode 接口'):
        states = upper_body.get_upper_fresh_mode()
        logger.debug(f"接口 get_upper_fresh_mode 返回：{states}")
    with allure.step("断言接口返回结果"):
        assert isinstance(states, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(states).__name__}: {states!r}'
    with allure.step("断言接口返回结果"):
        assert len(states) == 2, f'返回长度错误，期望 {2}，实际为 {len(states)}'
    with allure.step("断言接口返回结果"):
        assert all((state in (0, 1) for state in states))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
