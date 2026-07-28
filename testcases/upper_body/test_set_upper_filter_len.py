# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_upper_filter_len",
    required_columns=("title", "api", "target", "rank", "value", "expect_data", "test_type"),
)


@allure.feature("上半身滤波参数")
@allure.story("设置单臂和双臂滤波长度")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_upper_filter_len(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = case["expect_data"]
    target = case["target"]
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'rank:{case["rank"]}')
    logger.debug(f'value:{case["value"]}')

    with allure.step("读取左右臂原始滤波长度"):
        original_left = device.result_data(left_arm.get_upper_filter_len(case["rank"]))
        original_right = device.result_data(right_arm.get_upper_filter_len(case["rank"]))
    try:
        with allure.step(f"调用{target_name} set_upper_filter_len 接口"):
            actual = device.result_data(
                target_device.set_upper_filter_len(case["rank"], case["value"])
            )
        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
        with allure.step(f"回读并断言{target_name}滤波长度"):
            current = device.result_data(target_device.get_upper_filter_len(case["rank"]))
            if target == "both":
                assert list(current) == [case["value"], case["value"]]
            else:
                assert current == case["value"]
    finally:
        with allure.step("分别恢复左右臂原始滤波长度"):
            device.result_data(left_arm.set_upper_filter_len(case["rank"], original_left))
            device.result_data(right_arm.set_upper_filter_len(case["rank"], original_right))

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
