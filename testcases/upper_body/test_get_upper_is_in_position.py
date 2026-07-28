# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_is_in_position",
    required_columns=("title", "api", "target", "mode", "test_type"),
)


@allure.feature("上半身状态与参数查询")
@allure.story("查询单臂和双臂到位状态")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_is_in_position(device, upper_body, left_arm, right_arm, case):
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
    logger.debug(f'mode:{case["mode"]}')

    with allure.step(f"读取{target_name}当前关节角度"):
        current = device.result_data(target_device.get_upper_angles())
        if target == "both":
            assert isinstance(current, dict) and set(current) >= {"left", "right"}
            assert len(current["left"]) == 8 and len(current["right"]) == 8
        else:
            assert isinstance(current, (list, tuple)) and len(current) == 8

    with allure.step(f"调用{target_name} get_upper_is_in_position 接口"):
        if target == "both":
            result = upper_body.get_upper_is_in_position(
                case["mode"], left=current["left"], right=current["right"]
            )
        else:
            result = target_device.get_upper_is_in_position(case["mode"], current)
        actual = device.result_data(result)
        logger.debug(f"接口 get_upper_is_in_position 返回：{actual}")

    with allure.step(f"断言{target_name}到位状态返回结构"):
        if target == "both":
            assert isinstance(actual, (list, tuple)) and len(actual) == 2
            assert all(value in (0, 1, False, True) for value in actual)
        else:
            assert actual in (0, 1, False, True)

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
