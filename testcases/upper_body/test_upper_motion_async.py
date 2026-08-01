# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "upper_motion_async", required_columns=("title", "api", "enabled", "expect_data", "test_type"))
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身运动模式")
@allure.story("设置并读取上半身默认异步模式")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_upper_motion_async(upper_body, case):
    title = case["title"]
    expected = case["expect_data"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'enabled:{case["enabled"]}')
    with allure.step("读取原始默认异步模式"):
        original = upper_body.get_upper_motion_async()
    try:
        with allure.step("调用 set_upper_motion_async 设置默认异步模式"):
            actual = upper_body.set_upper_motion_async(case["enabled"])
            logger.debug(f"接口 set_upper_motion_async 返回：{actual}")
        with allure.step("断言设置接口返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(actual, bool)
            assert actual == expected
        with allure.step("调用 get_upper_motion_async 回读默认异步模式"):
            current = upper_body.get_upper_motion_async()
            allure.attach(str(expected), name="期望回读值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(current), name="实际回读值", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(current, bool)
            assert current == expected
    finally:
        with allure.step("恢复原始默认异步模式"):
            upper_body.set_upper_motion_async(original)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")


@allure.feature("上半身运动模式")
@allure.story("验证默认异步模式非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_upper_motion_async_exception(upper_body, case):
    title = case["title"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'enabled:{case["enabled"]}')
    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step("调用 set_upper_motion_async 设置非法参数"):
            upper_body.set_upper_motion_async(case["enabled"])
    logger.info("✅ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
