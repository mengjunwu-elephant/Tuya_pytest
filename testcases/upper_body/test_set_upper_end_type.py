# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_upper_end_type",
    required_columns=("title", "api", "target", "end_type", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身参数设置")
@allure.story("设置单臂和双臂末端类型")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_end_type(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = int(case["expect_data"])
    target = str(case["target"]).lower()
    end_type = int(case["end_type"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"end_type:{end_type}")

    with allure.step("读取左右臂原始末端类型"):
        original_left = device.result_data(left_arm.get_upper_end_type())
        original_right = device.result_data(right_arm.get_upper_end_type())
    try:
        with allure.step(f"调用{target_name} set_upper_end_type 接口"):
            if target == "both":
                result = upper_body.set_upper_end_type(left=end_type, right=end_type)
            else:
                result = target_device.set_upper_end_type(end_type)
            actual = device.result_data(result)
            logger.debug(f"接口 set_upper_end_type 返回：{actual}")

        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected

        with allure.step("分别回读左右臂末端类型"):
            current_left = device.result_data(left_arm.get_upper_end_type())
            current_right = device.result_data(right_arm.get_upper_end_type())
            if target == "left":
                assert current_left == end_type
                assert current_right == original_right
            elif target == "right":
                assert current_left == original_left
                assert current_right == end_type
            else:
                assert current_left == end_type
                assert current_right == end_type
    finally:
        with allure.step("分别恢复左右臂原始末端类型"):
            device.result_data(left_arm.set_upper_end_type(int(original_left)))
            device.result_data(right_arm.set_upper_end_type(int(original_right)))

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("上半身参数设置")
@allure.story("验证末端类型超限参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_upper_end_type_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    end_type = int(case["end_type"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"end_type:{end_type}")

    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step(f"调用{target_name} set_upper_end_type 接口并验证非法参数"):
            if target == "both":
                upper_body.set_upper_end_type(left=end_type, right=end_type)
            else:
                target_device.set_upper_end_type(end_type)
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
