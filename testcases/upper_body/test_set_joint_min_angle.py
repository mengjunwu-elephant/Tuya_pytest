# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_joint_min_angle",
    required_columns=('title', 'api', 'target', 'joint_id', 'degree', 'expect_data', 'test_type'),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身参数设置")
@allure.story("设置单臂和双臂关节最小角度")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_joint_min_angle(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = case["expect_data"]
    target = case["target"]
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    setting_value = case["degree"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'degree:{case["degree"]}')

    with allure.step("读取左右臂原始关节最小角度"):
        original_left_data = device.result_data(left_arm.get_upper_joints_min_angle())
        original_right_data = device.result_data(right_arm.get_upper_joints_min_angle())
        original_left = original_left_data[case["joint_id"] - 1]
        original_right = original_right_data[case["joint_id"] - 1]
    try:
        with allure.step(f"调用{target_name} set_joint_min_angle 接口"):
            if target == "both":
                result = upper_body.set_joint_min_angle(case["joint_id"], case["degree"])
            else:
                result = target_device.set_joint_min_angle(case["joint_id"], case["degree"])
            actual = device.result_data(result)
            logger.debug(f"接口 set_joint_min_angle 返回：{actual}")
        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
        with allure.step("分别回读左右臂关节最小角度"):
            current_left_data = device.result_data(left_arm.get_upper_joints_min_angle())
            current_right_data = device.result_data(right_arm.get_upper_joints_min_angle())
            current_left = current_left_data[case["joint_id"] - 1]
            current_right = current_right_data[case["joint_id"] - 1]
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
        with allure.step("分别恢复左右臂原始关节最小角度"):
            device.result_data(left_arm.set_joint_min_angle(case["joint_id"], original_left))
            device.result_data(right_arm.set_joint_min_angle(case["joint_id"], original_right))

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
