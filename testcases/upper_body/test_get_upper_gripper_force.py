# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "get_upper_gripper_force", required_columns=("title", "api", "target", "test_type"))


@allure.feature("上半身夹爪参数")
@allure.story("查询夹爪夹持力")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_gripper_force(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    target_device, target_name = {"left": (left_arm, "左臂"), "right": (right_arm, "右臂"), "both": (upper_body, "双臂")}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    with allure.step(f"调用{target_name} get_upper_gripper_force 接口"):
        actual = device.result_data(target_device.get_upper_gripper_force())
        param_actual = device.result_data(target_device.get_upper_gripper_param(1))
    with allure.step("断言夹持力返回结构与地址1参数一致"):
        if target == "both":
            assert isinstance(actual, dict) and set(actual) >= {"left", "right"}
            assert all(isinstance(actual[side], int) and not isinstance(actual[side], bool) for side in ("left", "right"))
        else:
            assert isinstance(actual, int) and not isinstance(actual, bool)
        assert actual == param_actual
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
