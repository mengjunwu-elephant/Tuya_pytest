# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation.errors import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_upper_fresh_mode",
    required_columns=("title", "api", "target", "state", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身运动模式")
@allure.story("设置单臂和双臂刷新模式")
@pytest.mark.upper_body
@pytest.mark.reset
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_fresh_mode(device, upper_body, left_arm, right_arm, case):
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
    logger.debug(f'state:{case["state"]}')

    with allure.step("读取左右臂原始刷新模式"):
        original = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original, (list, tuple)) and len(original) == 2
        original_left, original_right = original
    try:
        with allure.step(f"调用{target_name} set_upper_fresh_mode 接口"):
            actual = device.result_data(target_device.set_upper_fresh_mode(case["state"]))
        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
        with allure.step("回读并断言左右臂刷新模式"):
            current = device.result_data(upper_body.get_upper_fresh_mode())
            if target == "left":
                assert list(current) == [case["state"], original_right]
            elif target == "right":
                assert list(current) == [original_left, case["state"]]
            else:
                assert list(current) == [case["state"], case["state"]]
    finally:
        with allure.step("分别恢复左右臂原始刷新模式"):
            device.result_data(left_arm.set_upper_fresh_mode(original_left))
            device.result_data(right_arm.set_upper_fresh_mode(original_right))

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")


@allure.feature("上半身运动模式")
@allure.story("验证刷新模式非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_upper_fresh_mode_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[case["target"]]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'target:{case["target"]}')
    logger.debug(f'state:{case["state"]}')
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step("调用 set_upper_fresh_mode 接口并验证非法参数"):
            target_device.set_upper_fresh_mode(case["state"])
    logger.info("✅ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
