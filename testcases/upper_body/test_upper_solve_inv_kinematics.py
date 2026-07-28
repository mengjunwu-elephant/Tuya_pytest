# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "upper_solve_inv_kinematics",
    required_columns=("title", "api", "target", "test_type"),
)


@allure.feature("上半身运动学计算")
@allure.story("计算单臂和双臂逆运动学")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_upper_solve_inv_kinematics(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = case["target"]
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")

    with allure.step(f"读取{target_name}当前末端坐标"):
        current = device.result_data(target_device.get_upper_coords())
        if target == "both":
            assert isinstance(current, dict) and set(current) >= {"left", "right"}
            assert len(current["left"]) == 6 and len(current["right"]) == 6
        else:
            assert isinstance(current, (list, tuple)) and len(current) == 6

    with allure.step(f"调用{target_name} upper_solve_inv_kinematics 接口"):
        if target == "both":
            result = upper_body.upper_solve_inv_kinematics(
                current["left"], current["right"]
            )
        else:
            result = target_device.upper_solve_inv_kinematics(current)
        actual = device.result_data(result)
        logger.debug(f"接口 upper_solve_inv_kinematics 返回：{actual}")

    with allure.step(f"断言{target_name}逆运动学返回结构"):
        if target == "both":
            assert isinstance(actual, dict) and set(actual) >= {"left", "right"}
            assert len(actual["left"]) == 8 and len(actual["right"]) == 8
        else:
            assert isinstance(actual, (list, tuple)) and len(actual) == 8

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
