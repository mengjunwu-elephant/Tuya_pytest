# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_filter_len",
    required_columns=("title", "api", "target", "rank", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身滤波参数")
@allure.story("查询单臂和双臂滤波长度")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_get_upper_filter_len(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    rank = int(case["rank"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"rank:{rank}")

    with allure.step(f"调用{target_name} get_upper_filter_len 接口"):
        actual = device.result_data(target_device.get_upper_filter_len(rank))
        logger.debug(f"接口 get_upper_filter_len 返回：{actual}")

    with allure.step(f"断言{target_name}滤波长度返回结构"):
        if target == "both":
            assert isinstance(actual, (list, tuple)), f"双臂返回类型错误：{actual!r}"
            assert len(actual) == 2, f"双臂返回长度错误：{actual!r}"
            assert all(isinstance(value, int) and not isinstance(value, bool) for value in actual)
        else:
            assert isinstance(actual, int) and not isinstance(actual, bool), f"单臂返回类型错误：{actual!r}"

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("上半身滤波参数")
@allure.story("验证滤波长度查询非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_get_upper_filter_len_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    rank = int(case["rank"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"rank:{rank}")

    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step(f"调用{target_name} get_upper_filter_len 接口并验证非法参数"):
            target_device.get_upper_filter_len(rank)
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
