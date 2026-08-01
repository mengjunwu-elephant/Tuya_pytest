# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_collision_mode",
    required_columns=("title", "api", "target", "expect_data", "test_type"),
)


@allure.feature("上半身碰撞参数")
@allure.story("查询单臂和双臂碰撞模式")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_upper_collision_mode(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = case["target"]
    expected = int(case["expect_data"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")

    with allure.step(f"调用{target_name} get_upper_collision_mode 接口"):
        result = target_device.get_upper_collision_mode()
        actual = device.result_data(result)
        logger.debug(f"接口 get_upper_collision_mode 返回：{actual}")

    with allure.step(f"断言{target_name}碰撞模式"):
        if target == "both":
            expected_both = {"left": expected, "right": expected}
            allure.attach(str(expected_both), name="期望碰撞模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际碰撞模式", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(actual, dict), f"双臂碰撞模式应返回 dict，实际: {actual!r}"
            assert set(actual) >= {"left", "right"}, f"双臂碰撞模式缺少左右臂键，实际: {actual!r}"
            for side in ("left", "right"):
                value = actual[side]
                assert isinstance(value, int) and not isinstance(value, bool), (
                    f"{side} 碰撞模式类型错误：{value!r}"
                )
            assert {side: actual[side] for side in ("left", "right")} == expected_both
        else:
            allure.attach(str(expected), name="期望碰撞模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际碰撞模式", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(actual, int) and not isinstance(actual, bool), (
                f"单臂碰撞模式应返回 int，实际: {actual!r}"
            )
            assert actual == expected

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
