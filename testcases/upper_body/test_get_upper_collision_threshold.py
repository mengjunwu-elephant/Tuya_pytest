# -*- coding: utf-8 -*-
import json

import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_collision_threshold",
    required_columns=("title", "api", "arm", "expect_data", "test_type"),
)


@allure.feature("上半身碰撞参数")
@allure.story("查询单臂碰撞阈值")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_collision_threshold(device, left_arm, right_arm, case):
    title = case["title"]
    arm = case["arm"]
    expected = (
        json.loads(case["expect_data"])
        if isinstance(case["expect_data"], str)
        else case["expect_data"]
    )
    target_device, target_name = (left_arm, "左臂") if arm == "left" else (right_arm, "右臂")
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"arm:{arm}")
    with allure.step(f"调用{target_name} get_upper_collision_threshold 接口"):
        actual = device.result_data(target_device.get_upper_collision_threshold())
        logger.debug(f"接口 get_upper_collision_threshold 返回：{actual}")
    with allure.step(f"断言{target_name}碰撞阈值"):
        allure.attach(str(expected), name="期望碰撞阈值", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(actual), name="实际碰撞阈值", attachment_type=allure.attachment_type.TEXT)
        assert isinstance(actual, (list, tuple)), f"单臂碰撞阈值应返回 list，实际: {actual!r}"
        assert len(actual) == 7, f"碰撞阈值长度错误：{actual!r}"
        assert all(isinstance(value, int) and not isinstance(value, bool) for value in actual), (
            f"碰撞阈值元素类型错误：{actual!r}"
        )
        assert list(actual) == list(expected)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
