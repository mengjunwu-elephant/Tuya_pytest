# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_world_reference",
    required_columns=("title", "api", "test_type"),
)


@allure.feature("上半身状态与参数查询")
@allure.story("查询双臂世界参考系")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_world_reference(device, upper_body, case):
    title = case["title"]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')

    with allure.step("调用双臂 get_upper_world_reference 接口"):
        actual = device.result_data(upper_body.get_upper_world_reference())
        logger.debug(f"接口 get_upper_world_reference 返回：{actual}")

    with allure.step("断言双臂世界参考系返回结构"):
        assert isinstance(actual, dict), f"双臂返回类型错误：{actual!r}"
        assert set(actual) >= {"left", "right"}, f"双臂返回缺少 left/right：{actual!r}"
        for arm_name in ("left", "right"):
            arm_data = actual[arm_name]
            assert isinstance(arm_data, (list, tuple)), f"{arm_name} 数据类型错误：{arm_data!r}"
            assert len(arm_data) == 6, f"{arm_name} 数据长度错误：{arm_data!r}"
            assert all(
                isinstance(value, (int, float)) and not isinstance(value, bool) for value in arm_data
            ), f"{arm_name} 元素类型错误：{arm_data!r}"

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
