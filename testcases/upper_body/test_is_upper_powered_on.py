# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "is_upper_powered_on",
    required_columns=(
        "title",
        "api",
        "target",
        "expect_powered_off",
        "expect_powered_on",
        "test_type",
    ),
)


@allure.feature("上半身上下电")
@allure.story("查询单臂和双臂上下电状态")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_is_upper_powered_on(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    expect_off = int(case["expect_powered_off"])
    expect_on = int(case["expect_powered_on"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")

    try:
        with allure.step(f"调用{target_name}下电并等待下电完成"):
            device.result_data(target_device.upper_power_off())
            deadline = time.monotonic() + 30
            while True:
                off_state = device.result_data(target_device.is_upper_powered_on())
                logger.debug(f"接口 is_upper_powered_on 下电返回：{off_state}")
                if target == "both":
                    if isinstance(off_state, (list, tuple)) and len(off_state) == 2 and list(off_state) == [expect_off, expect_off]:
                        break
                elif isinstance(off_state, int) and not isinstance(off_state, bool) and off_state == expect_off:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"{target_name}未在 30 秒内下电，期望：{expect_off!r}，实际：{off_state!r}"
                    )
                time.sleep(0.2)

        with allure.step(f"断言{target_name}下电状态"):
            expected_off_value = [expect_off, expect_off] if target == "both" else expect_off
            allure.attach(str(expected_off_value), name="期望下电状态", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(off_state), name="实际下电状态", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert list(off_state) == [expect_off, expect_off]
            else:
                assert off_state == expect_off

        with allure.step(f"调用{target_name}上电并等待上电完成"):
            device.result_data(target_device.upper_power_on())
            deadline = time.monotonic() + 30
            while True:
                on_state = device.result_data(target_device.is_upper_powered_on())
                logger.debug(f"接口 is_upper_powered_on 上电返回：{on_state}")
                if target == "both":
                    if isinstance(on_state, (list, tuple)) and len(on_state) == 2 and list(on_state) == [expect_on, expect_on]:
                        break
                elif isinstance(on_state, int) and not isinstance(on_state, bool) and on_state == expect_on:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"{target_name}未在 30 秒内上电，期望：{expect_on!r}，实际：{on_state!r}"
                    )
                time.sleep(0.2)

        with allure.step(f"断言{target_name}上电状态"):
            expected_on_value = [expect_on, expect_on] if target == "both" else expect_on
            allure.attach(str(expected_on_value), name="期望上电状态", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(on_state), name="实际上电状态", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert list(on_state) == [expect_on, expect_on]
            else:
                assert on_state == expect_on
    finally:
        with allure.step("恢复双臂上电状态"):
            device.result_data(upper_body.upper_power_on())
            deadline = time.monotonic() + 30
            while True:
                restored = device.result_data(upper_body.is_upper_powered_on())
                if list(restored) == [1, 1]:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"未在 30 秒内恢复双臂上电，实际：{restored!r}")
                time.sleep(0.2)

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
