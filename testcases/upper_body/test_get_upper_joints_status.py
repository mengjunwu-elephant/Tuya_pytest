# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_joints_status",
    required_columns=('title', 'api', 'target', 'test_type'),
)


@allure.feature("上半身状态与参数查询")
@allure.story("查询单臂和双臂关节状态")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_joints_status(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = case["target"]
    targets = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }
    target_device, target_name = targets[target]

    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")

    with allure.step(f"调用{target_name} get_upper_joints_status 接口"):
        result = target_device.get_upper_joints_status()
        actual = device.result_data(result)
        logger.debug(f"接口 get_upper_joints_status 返回：{actual}")

    with allure.step(f"断言{target_name}关节状态返回结构"):
        if target == "both":
            assert isinstance(actual, dict), f"双臂返回类型错误：{actual!r}"
            assert set(actual) >= {"left", "right"}, f"双臂返回缺少 left/right：{actual!r}"
        else:
            assert isinstance(actual, (dict, list, tuple)), f"单臂返回类型错误：{actual!r}"

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
