# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "upper_power_off")


@allure.feature("上半身上下电")
@allure.story("上半身双臂下电")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_upper_power_off(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = case["expect_data"]
    expected_states = [case["expect_left_state"], case["expect_right_state"]]

    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'target:{case["target"]}')

    with allure.step("读取测试前的双臂上电状态"):
        original = device.result_data(upper_body.is_upper_powered_on())
        logger.debug(f"测试前双臂上电状态：{original}")
        assert isinstance(original, (list, tuple)), f"上电状态类型错误：{original!r}"
        assert len(original) == 2, f"上电状态长度错误：{original!r}"
        original = list(original)

    try:
        with allure.step("调用双臂 upper_power_off 接口"):
            result = upper_body.upper_power_off()
            actual = device.result_data(result)
            logger.debug("接口 upper_power_off 真实入参：无")
            logger.debug(f"接口 upper_power_off 返回：{actual}")

        with allure.step("断言下电接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(actual, int) and not isinstance(actual, bool), f"双臂下电返回类型错误：{actual!r}"
            assert actual == expected

        with allure.step("等待并验证双臂下电状态"):
            deadline = time.monotonic() + 30
            while True:
                states = device.result_data(upper_body.is_upper_powered_on())
                if list(states) == expected_states:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "双臂未在 30 秒内达到期望下电状态，"
                        f"期望：{expected_states!r}，实际：{states!r}"
                    )
                time.sleep(0.2)
            allure.attach(str(expected_states), name="期望下电状态", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(states), name="实际下电状态", attachment_type=allure.attachment_type.TEXT)
    finally:
        with allure.step("恢复测试前的双臂上电状态"):
            if original == [1, 1]:
                device.result_data(upper_body.upper_power_on())
            elif original[0] == 1:
                device.result_data(left_arm.upper_power_on())
            elif original[1] == 1:
                device.result_data(right_arm.upper_power_on())
            deadline = time.monotonic() + 30
            while True:
                restored_states = device.result_data(upper_body.is_upper_powered_on())
                if list(restored_states) == original:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "未在 30 秒内恢复测试前的双臂上电状态，"
                        f"期望：{original!r}，实际：{restored_states!r}"
                    )
                time.sleep(0.2)

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
