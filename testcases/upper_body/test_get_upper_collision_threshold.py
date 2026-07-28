# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_collision_threshold",
)


@allure.feature("上半身碰撞参数")
@allure.story("查询单臂碰撞阈值原始响应")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_collision_threshold(device, left_arm, right_arm, case):
    title = case["title"]
    arm = case["arm"]
    target_device, target_name = (left_arm, "左臂") if arm == "left" else (right_arm, "右臂")
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"arm:{arm}")
    with allure.step(f"调用{target_name} get_upper_collision_threshold 接口"):
        actual = device.result_data(target_device.get_upper_collision_threshold())
        logger.debug(f"接口 get_upper_collision_threshold 返回：{actual}")
    with allure.step("断言SDK当前返回原始碰撞参数字节"):
        assert isinstance(actual, (bytes, bytearray)), f"SDK当前应返回原始字节：{actual!r}"
        assert len(actual) >= 1, f"碰撞参数原始响应为空：{actual!r}"
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
