# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_is_paused",
    required_columns=(
        "title",
        "api",
        "target",
        "expect_paused",
        "test_type",
    ),
)
manual_cases = [case for case in cases if case["test_type"] == "manual"]


def _as_flag(value):
    assert isinstance(value, (int, bool)), f"暂停状态类型错误：{value!r}"
    return int(value)


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("暂停状态查询全部用例结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        assert upper_body.set_upper_motion_async(False) is False
        device.result_data(upper_body.upper_resume())
        device.go_zero()


@allure.feature("上半身状态与参数查询")
@allure.story("插补模式下暂停状态")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_get_upper_is_paused(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    expect_paused = int(case["expect_paused"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    left_angles = list(TuyaRobotBase.COORD_MOTION_INITIAL_ANGLES["left"])
    right_angles = list(TuyaRobotBase.COORD_MOTION_INITIAL_ANGLES["right"])
    speed = TuyaRobotBase.speed

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")

    try:
        with allure.step("先设置双臂插补模式并回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            device.go_zero()

        with allure.step(f"异步下发{target_name}坐标初始姿态以便运动中暂停"):
            if target == "left":
                device.result_data(left_arm.send_upper_angles(left_angles, speed, 0, _async=True))
            elif target == "right":
                device.result_data(right_arm.send_upper_angles(right_angles, speed, 0, _async=True))
            else:
                device.result_data(
                    upper_body.send_upper_angles(
                        left_angles, speed, 0, right_angles, speed, 0, _async=True
                    )
                )

        with allure.step("运动开始后等待0.3s并下发暂停指令"):
            time.sleep(0.3)
            device.result_data(target_device.upper_pause())

        with allure.step(f"断言{target_name}暂停状态"):
            paused = device.result_data(target_device.get_upper_is_paused())
            logger.debug(f"接口 get_upper_is_paused 返回：{paused}")
            expected_value = [expect_paused, expect_paused] if target == "both" else expect_paused
            allure.attach(str(expected_value), name="期望暂停状态", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(paused), name="实际暂停状态", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert isinstance(paused, (list, tuple)) and len(paused) == 2, f"双臂暂停状态结构错误：{paused!r}"
                assert [_as_flag(value) for value in paused] == [expect_paused, expect_paused]
            else:
                assert _as_flag(paused) == expect_paused

        with allure.step(f"调用{target_name} upper_resume 恢复运动"):
            device.result_data(target_device.upper_resume())
    finally:
        with allure.step("确保恢复运动、双臂插补模式并回零"):
            device.result_data(target_device.upper_resume())
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
