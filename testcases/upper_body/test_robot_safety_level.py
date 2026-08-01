# -*- coding: utf-8 -*-
import json

import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "robot_safety_level", required_columns=("title", "api", "level", "expect_data", "test_type"))
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("整机安全策略")
@allure.story("设置并读取整机安全等级")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_robot_safety_level(device, robot, case):
    title = case["title"]
    level = json.loads(case["level"]) if isinstance(case["level"], str) else case["level"]
    expected = json.loads(case["expect_data"]) if isinstance(case["expect_data"], str) else case["expect_data"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"level:{level}")
    with allure.step("读取原始整机安全等级"):
        original = robot.get_robot_safety_level()
    try:
        with allure.step("调用 set_robot_safety_level 设置安全等级"):
            actual = device.result_data(robot.set_robot_safety_level(level))
        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
        with allure.step("调用 get_robot_safety_level 回读安全等级"):
            current = robot.get_robot_safety_level()
            assert current == expected
    finally:
        with allure.step("恢复原始整机安全等级"):
            robot.set_robot_safety_level(original)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")


@allure.feature("整机安全策略")
@allure.story("验证整机安全等级非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_robot_safety_level_exception(robot, case):
    title = case["title"]
    level = json.loads(case["level"]) if isinstance(case["level"], str) else case["level"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"level:{level}")
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step("调用 set_robot_safety_level 校验非法参数"):
            robot.set_robot_safety_level(level)
    logger.info("✅ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
