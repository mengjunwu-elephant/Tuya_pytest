# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation.errors import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'set_upper_debug_state')
normal_cases = [case for case in cases if case['test_type'] == 'normal']
exception_cases = [case for case in cases if case['test_type'] == 'exception']

@allure.feature('UpperBody')
@allure.story('set_upper_debug_state')
@pytest.mark.upper_body
@pytest.mark.reset
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_debug_state(upper_body, case):
    title = case['title']
    expected = case["expect_data"]
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'state:{case["state"]}')
    with allure.step('调用 get_upper_debug_state 接口'):
        original = upper_body.get_upper_debug_state()
        logger.debug(f"接口 get_upper_debug_state 返回：{original}")
    with allure.step("断言接口返回结果"):
        assert isinstance(original, int) and (not isinstance(original, bool)), f'返回类型错误，期望 int，实际为 {type(original).__name__}: {original!r}'
    try:
        with allure.step('调用 set_upper_debug_state 接口'):
            upper_body.set_upper_debug_state(case['state'])
        with allure.step('调用 get_upper_debug_state 接口'):
            actual = upper_body.get_upper_debug_state()
            logger.debug(f"接口 get_upper_debug_state 返回：{actual}")
        with allure.step("断言接口返回结果"):
            assert isinstance(actual, int) and (not isinstance(actual, bool)), f'返回类型错误，期望 int，实际为 {type(actual).__name__}: {actual!r}'
        with allure.step("断言接口返回结果"):
            allure.attach(str(expected), name="期望值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
    finally:
        with allure.step('调用 set_upper_debug_state 接口'):
            upper_body.set_upper_debug_state(original)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')

@allure.feature('UpperBody')
@allure.story('set_upper_debug_state')
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_upper_debug_state_exception(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'state:{case["state"]}')
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step('调用 set_upper_debug_state 接口'):
            upper_body.set_upper_debug_state(case['state'])
    logger.info("✅ 异常断言通过,异常信息：%s", exc.value)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
