# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_filter_len",
    required_columns=("title", "api", "target", "rank", "test_type"),
)


@allure.feature("上半身滤波参数")
@allure.story("查询单臂和双臂滤波长度")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_filter_len(device, upper_body, left_arm, right_arm, case):
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
    logger.debug(f'rank:{case["rank"]}')

    with allure.step(f"调用{target_name} get_upper_filter_len 接口"):
        result = target_device.get_upper_filter_len(case["rank"])
        actual = device.result_data(result)
        logger.debug(f"接口 get_upper_filter_len 返回：{actual}")

    with allure.step(f"断言{target_name}滤波长度返回结构"):
        if target == "both":
            assert isinstance(actual, (list, tuple)) and len(actual) == 2
            assert all(isinstance(value, int) and not isinstance(value, bool) for value in actual)
        else:
            assert isinstance(actual, int) and not isinstance(actual, bool)

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
