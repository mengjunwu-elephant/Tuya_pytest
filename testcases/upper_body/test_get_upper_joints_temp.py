# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "get_upper_joints_temp", required_columns=("title", "api", "target", "test_type"))


@allure.feature("上半身温度状态")
@allure.story("查询关节温度")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_joints_temp(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    target_device, target_name = {"left": (left_arm, "左臂"), "right": (right_arm, "右臂"), "both": (upper_body, "双臂")}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    with allure.step(f"调用{target_name} get_upper_joints_temp 接口"):
        actual = device.result_data(target_device.get_upper_joints_temp())
        gripper_temp = device.result_data(target_device.get_upper_gripper_temp())
    with allure.step("断言关节温度结构并校验J8夹爪温度一致"):
        if target == "both":
            assert isinstance(actual, dict) and set(actual) >= {"left", "right"}
            assert isinstance(gripper_temp, dict) and set(gripper_temp) >= {"left", "right"}
            for side in ("left", "right"):
                assert isinstance(actual[side], (list, tuple)) and len(actual[side]) == 8
                assert all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in actual[side])
                assert actual[side][7] == gripper_temp[side]
        else:
            assert isinstance(actual, (list, tuple)) and len(actual) == 8
            assert all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in actual)
            assert actual[7] == gripper_temp
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
