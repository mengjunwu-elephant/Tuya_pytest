# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_joints_max_angle",
    required_columns=("title", "api", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]


@allure.feature("上半身状态与参数查询")
@allure.story("查询上半身关节最大角度")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_get_upper_joints_max_angle(device, upper_body, case):
    title = case["title"]
    expected = [
        TuyaRobotBase.UPPER_BODY_JOINT_SOFT_LIMITS[joint_id][1]
        for joint_id in range(1, 8)
    ]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')

    with allure.step("调用 get_upper_joints_max_angle 接口"):
        actual = device.result_data(upper_body.get_upper_joints_max_angle())
        logger.debug(f"接口 get_upper_joints_max_angle 返回：{actual}")

    with allure.step("断言返回结构为8关节列表"):
        assert isinstance(actual, (list, tuple)), f"返回类型错误：{actual!r}"
        assert len(actual) == 8, f"返回长度错误，期望8，实际：{len(actual)}"
        assert all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in actual)

    with allure.step("断言J1到J7等于软件上限"):
        allure.attach(str(expected), name="期望J1到J7软件上限", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(list(actual[:7])), name="实际J1到J7最大角度", attachment_type=allure.attachment_type.TEXT)
        assert list(actual[:7]) == expected

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
