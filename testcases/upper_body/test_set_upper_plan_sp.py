# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_upper_plan_sp",
    required_columns=('title', 'api', 'target', 'mode', 'speed', 'expect_data', 'test_type'),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身参数设置")
@allure.story("设置单臂和双臂规划速度")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_plan_sp(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = case["expect_data"]
    target = case["target"]
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    setting_value = case["speed"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'mode:{case["mode"]}')
    logger.debug(f'speed:{case["speed"]}')

    with allure.step("读取左右臂原始规划速度"):
        original_left_data = device.result_data(left_arm.get_upper_plan_sp(case["mode"]))
        original_right_data = device.result_data(right_arm.get_upper_plan_sp(case["mode"]))
        original_left = original_left_data
        original_right = original_right_data
    try:
        with allure.step(f"调用{target_name} set_upper_plan_sp 接口"):
            if target == "both":
                result = upper_body.set_upper_plan_sp(case["mode"], case["speed"])
            else:
                result = target_device.set_upper_plan_sp(case["mode"], case["speed"])
            actual = device.result_data(result)
            logger.debug(f"接口 set_upper_plan_sp 返回：{actual}")
        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
        with allure.step("分别回读左右臂规划速度"):
            current_left_data = device.result_data(left_arm.get_upper_plan_sp(case["mode"]))
            current_right_data = device.result_data(right_arm.get_upper_plan_sp(case["mode"]))
            current_left = current_left_data
            current_right = current_right_data
            if target == "left":
                assert current_left == setting_value
                assert current_right == original_right
            elif target == "right":
                assert current_left == original_left
                assert current_right == setting_value
            else:
                assert current_left == setting_value
                assert current_right == setting_value
    finally:
        with allure.step("分别恢复左右臂原始规划速度"):
            device.result_data(left_arm.set_upper_plan_sp(case["mode"], original_left))
            device.result_data(right_arm.set_upper_plan_sp(case["mode"], original_right))

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
