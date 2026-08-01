# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_joint_acc",
    required_columns=("title", "api", "target", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]


def _assert_joint_acc_block(values, name):
    assert isinstance(values, (list, tuple)), f"{name}返回类型错误：{values!r}"
    assert len(values) == 7, f"{name}长度错误，期望7，实际：{len(values)}"
    for index, value in enumerate(values, start=1):
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"{name} J{index} 类型错误：{value!r}"
        )


@allure.feature("上半身状态与参数查询")
@allure.story("查询单臂和双臂关节加速度")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_get_upper_joint_acc(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")

    with allure.step(f"调用{target_name} get_upper_joint_acc 接口"):
        actual = device.result_data(target_device.get_upper_joint_acc())
        logger.debug(f"接口 get_upper_joint_acc 返回：{actual}")

    with allure.step(f"断言{target_name}关节加速度返回结构"):
        if target == "both":
            assert isinstance(actual, dict), f"双臂返回类型错误：{actual!r}"
            assert set(actual) >= {"left", "right"}, f"双臂返回缺少 left/right：{actual!r}"
            _assert_joint_acc_block(actual["left"], "左臂")
            _assert_joint_acc_block(actual["right"], "右臂")
        else:
            _assert_joint_acc_block(actual, target_name)

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
