# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "set_upper_gripper_force", required_columns=("title", "api", "target", "value", "expect_data", "test_type"))
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身夹爪参数")
@allure.story("设置夹爪夹持力")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_gripper_force(device, upper_body, left_arm, right_arm, case):
    title, target, value = case["title"], case["target"], case["value"]
    target_device, target_name = {"left": (left_arm, "左臂"), "right": (right_arm, "右臂"), "both": (upper_body, "双臂")}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}, value:{value}")
    with allure.step("读取左右臂原始夹持力"):
        original_left = device.result_data(left_arm.get_upper_gripper_force())
        original_right = device.result_data(right_arm.get_upper_gripper_force())
    try:
        with allure.step(f"调用{target_name} set_upper_gripper_force 接口"):
            actual = device.result_data(target_device.set_upper_gripper_force(value))
        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(case["expect_data"]), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == case["expect_data"]
        with allure.step("分别回读左右臂夹持力"):
            current_left = device.result_data(left_arm.get_upper_gripper_force())
            current_right = device.result_data(right_arm.get_upper_gripper_force())
            assert current_left == (value if target in ("left", "both") else original_left)
            assert current_right == (value if target in ("right", "both") else original_right)
    finally:
        with allure.step("分别恢复左右臂原始夹持力"):
            device.result_data(left_arm.set_upper_gripper_force(original_left))
            device.result_data(right_arm.set_upper_gripper_force(original_right))
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")


@allure.feature("上半身夹爪参数")
@allure.story("验证夹爪夹持力非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_upper_gripper_force_exception(upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'target:{target}, value:{case["value"]}')
    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step("调用 set_upper_gripper_force 校验非法参数"):
            target_device.set_upper_gripper_force(case["value"])
    logger.info("✅ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
