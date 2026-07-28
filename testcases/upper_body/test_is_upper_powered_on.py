# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "is_upper_powered_on")


@allure.feature("上半身上下电")
@allure.story("查询上半身上电状态")
@pytest.mark.upper_body
@pytest.mark.smoke
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_is_upper_powered_on(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = case["expect_data"]
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

    with allure.step(f"调用{target_name} is_upper_powered_on 接口"):
        result = target_device.is_upper_powered_on()
        actual = device.result_data(result)
        logger.debug(f"接口 is_upper_powered_on 真实入参：target={target}")
        logger.debug(f"接口 is_upper_powered_on 返回：{actual}")

    with allure.step(f"断言{target_name}上电状态"):
        allure.attach(str(expected), name="期望上电状态", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(actual), name="实际上电状态", attachment_type=allure.attachment_type.TEXT)
        if target == "both":
            assert isinstance(actual, (list, tuple)), f"双臂上电状态类型错误：{actual!r}"
            assert len(actual) == 2, f"双臂上电状态长度错误：{actual!r}"
            assert list(actual) == [expected, expected]
        else:
            assert isinstance(actual, int) and not isinstance(actual, bool), f"单臂上电状态类型错误：{actual!r}"
            assert actual == expected

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
