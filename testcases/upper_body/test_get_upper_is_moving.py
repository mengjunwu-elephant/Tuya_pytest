# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_is_moving",
    required_columns=(
        "title",
        "api",
        "target",
        "expect_moving",
        "expect_stopped",
        "test_type",
    ),
)
manual_cases = [case for case in cases if case["test_type"] == "manual"]


def _as_flag(value):
    assert isinstance(value, (int, bool)), f"运动状态类型错误：{value!r}"
    return int(value)


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("运动状态查询全部用例结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        assert upper_body.set_upper_motion_async(False) is False
        device.go_zero()


@allure.feature("上半身状态与参数查询")
@allure.story("刷新模式下运动中与静止状态")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_get_upper_is_moving(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    expect_moving = int(case["expect_moving"])
    expect_stopped = int(case["expect_stopped"])
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

    with allure.step("读取运动前双臂刷新模式和默认异步状态"):
        original_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original_modes, (list, tuple)) and len(original_modes) == 2
        original_motion_async = upper_body.get_upper_motion_async()
        assert isinstance(original_motion_async, bool)

    try:
        with allure.step("先回零以保证存在运动行程"):
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

        with allure.step(f"异步下发{target_name}坐标初始姿态"):
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

        with allure.step("运动开始后等待100ms并读取运动中状态"):
            time.sleep(0.1)
            moving = device.result_data(target_device.get_upper_is_moving())
            logger.debug(f"接口 get_upper_is_moving 运动中返回：{moving}")
            allure.attach(str(expect_moving if target != "both" else [expect_moving, expect_moving]), name="期望运动中状态", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(moving), name="实际运动中状态", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert isinstance(moving, (list, tuple)) and len(moving) == 2, f"双臂运动状态结构错误：{moving!r}"
                assert [_as_flag(value) for value in moving] == [expect_moving, expect_moving]
            else:
                assert _as_flag(moving) == expect_moving

        with allure.step(f"等待{target_name}静止并断言静止状态"):
            deadline = time.monotonic() + 30
            stopped = None
            while True:
                stopped = device.result_data(target_device.get_upper_is_moving())
                if target == "both":
                    if isinstance(stopped, (list, tuple)) and len(stopped) == 2 and [_as_flag(value) for value in stopped] == [expect_stopped, expect_stopped]:
                        break
                elif _as_flag(stopped) == expect_stopped:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"{target_name}未在 30 秒内静止，最后状态：{stopped!r}"
                    )
                time.sleep(0.1)
            logger.debug(f"接口 get_upper_is_moving 静止返回：{stopped}")
            allure.attach(str(expect_stopped if target != "both" else [expect_stopped, expect_stopped]), name="期望静止状态", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(stopped), name="实际静止状态", attachment_type=allure.attachment_type.TEXT)
    finally:
        with allure.step("恢复原始刷新模式、默认异步状态并回零"):
            assert device.result_data(left_arm.set_upper_fresh_mode(original_modes[0])) == 1
            assert device.result_data(right_arm.set_upper_fresh_mode(original_modes[1])) == 1
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
