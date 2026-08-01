# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.command_result import CommandResult
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "upper_stop",
    required_columns=(
        "title",
        "api",
        "target",
        "fresh_mode",
        "expect_data",
        "expect_state",
        "message",
        "test_type",
    ),
)
manual_cases = [
    case for case in cases if case["test_type"] == "manual" and int(case["fresh_mode"]) == 0
]
unsupported_cases = [
    case for case in cases if case["test_type"] == "manual" and int(case["fresh_mode"]) == 1
]


def _as_flag(value):
    assert isinstance(value, (int, bool)), f"运动状态类型错误：{value!r}"
    return int(value)


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("停止运动全部用例结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        assert upper_body.set_upper_motion_async(False) is False
        device.go_zero()


@allure.feature("上半身运动控制")
@allure.story("插补模式下运动过程中停止")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_upper_stop(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    expected = int(case["expect_data"])
    expect_state = int(case["expect_state"])
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
    logger.debug(f'fresh_mode:{case["fresh_mode"]}')

    try:
        with allure.step("先设置双臂插补模式并回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            device.go_zero()

        with allure.step(f"异步下发{target_name}坐标初始姿态以便运动中停止"):
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

        with allure.step(f"运动开始后等待0.3s并调用{target_name} upper_stop"):
            time.sleep(0.3)
            actual = device.result_data(target_device.upper_stop())
            logger.debug(f"接口 upper_stop 返回：{actual}")

        with allure.step("断言停止接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected

        with allure.step(f"断言{target_name}运动状态为静止"):
            moving = device.result_data(target_device.get_upper_is_moving())
            logger.debug(f"接口 get_upper_is_moving 返回：{moving}")
            expected_moving = [expect_state, expect_state] if target == "both" else expect_state
            allure.attach(str(expected_moving), name="期望运动状态", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(moving), name="实际运动状态", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert isinstance(moving, (list, tuple)) and len(moving) == 2, f"双臂运动状态结构错误：{moving!r}"
                assert [_as_flag(value) for value in moving] == [expect_state, expect_state]
            else:
                assert _as_flag(moving) == expect_state
    finally:
        with allure.step("恢复双臂插补模式并回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("上半身运动控制")
@allure.story("刷新模式不支持停止运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", unsupported_cases, ids=lambda c: c["title"])
def test_upper_stop_refresh_mode_unsupported(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    expected_message = str(case["message"])

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'fresh_mode:{case["fresh_mode"]}')

    try:
        with allure.step("先设置双臂插补模式并回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            device.go_zero()

        with allure.step(f"设置{target_name}为刷新模式"):
            assert device.result_data(target_device.set_upper_fresh_mode(1)) == 1
            modes = device.result_data(upper_body.get_upper_fresh_mode())
            assert isinstance(modes, (list, tuple)) and len(modes) == 2
            if target == "left":
                assert modes[0] == 1
            elif target == "right":
                assert modes[1] == 1
            else:
                assert list(modes) == [1, 1]

        with allure.step("刷新模式下显式启用默认异步状态"):
            assert upper_body.set_upper_motion_async(True) is True

        with allure.step(f"刷新模式下调用{target_name} upper_stop"):
            result = target_device.upper_stop()
            logger.debug(f"接口 upper_stop 返回：{result}")

        with allure.step("断言刷新模式不支持停止运动"):
            assert isinstance(result, CommandResult), f"刷新模式 stop 应返回 CommandResult，实际: {result!r}"
            allure.attach(expected_message, name="期望错误信息", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(result.message), name="实际错误信息", attachment_type=allure.attachment_type.TEXT)
            assert result.ok is False
            assert expected_message in (result.message or ""), (
                f"错误信息不一致，期望包含: {expected_message}，实际: {result.message}"
            )
    finally:
        with allure.step("恢复双臂插补模式并回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
