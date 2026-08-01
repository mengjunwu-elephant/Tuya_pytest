# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "upper_go_zero",
    required_columns=(
        "title",
        "api",
        "target",
        "fresh_mode",
        "expect_data",
        "test_type",
    ),
)
manual_cases = [case for case in cases if case["test_type"] == "manual"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("upper_go_zero 全部用例结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        assert upper_body.set_upper_motion_async(False) is False
        device.go_zero()


@allure.feature("上半身回零运动")
@allure.story("刷新与插补模式下单臂和双臂回零")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_upper_go_zero(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    fresh_mode = int(case["fresh_mode"])
    expected = int(case["expect_data"])
    mode_name = "刷新模式" if fresh_mode == 1 else "插补模式"
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    zero_angles = list(TuyaRobotBase.UPPER_BODY_ZERO_ANGLES)

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"fresh_mode:{fresh_mode}")

    try:
        with allure.step("先设置双臂插补模式并进入坐标初始姿态"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            initial_actual = device.move_to_coord_initial_pose(None if target == "both" else target)
            allure.attach(str(initial_actual), name="实际坐标初始点位", attachment_type=allure.attachment_type.TEXT)

        with allure.step(f"设置{target_name}为{mode_name}"):
            assert device.result_data(target_device.set_upper_fresh_mode(fresh_mode)) == 1
            modes = device.result_data(upper_body.get_upper_fresh_mode())
            assert isinstance(modes, (list, tuple)) and len(modes) == 2
            if target == "left":
                assert modes[0] == fresh_mode
            elif target == "right":
                assert modes[1] == fresh_mode
            else:
                assert list(modes) == [fresh_mode, fresh_mode]

        with allure.step(f"设置{mode_name}对应的默认异步状态"):
            expected_motion_async = fresh_mode == 1
            assert upper_body.set_upper_motion_async(expected_motion_async) is expected_motion_async

        with allure.step(f"调用{target_name} upper_go_zero 接口"):
            result = target_device.upper_go_zero(_async=(fresh_mode == 1))
            actual = device.result_data(result)
            logger.debug(f"接口 upper_go_zero 返回：{actual}")

        with allure.step("断言回零接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected

        with allure.step(f"等待{target_name}回零完成并断言零位角度"):
            if fresh_mode == 1:
                deadline = time.monotonic() + 30
                while True:
                    moving = device.result_data(target_device.get_upper_is_moving())
                    if target == "both":
                        if isinstance(moving, (list, tuple)) and list(moving) == [0, 0]:
                            break
                    elif int(moving) == 0:
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"{target_name}未在 30 秒内完成回零，运动状态：{moving!r}")
                    time.sleep(0.1)
            else:
                device.wait_upper(timeout=30)

            angles = device.result_data(target_device.get_upper_angles())
            allure.attach(str(zero_angles), name="期望零位角度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(angles), name="实际回零角度", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert isinstance(angles, dict) and set(angles) >= {"left", "right"}
                assert_almost_equal(
                    list(angles["left"]),
                    zero_angles,
                    tol=TuyaRobotBase.angle_tolerance,
                    name="左臂回零角度",
                )
                assert_almost_equal(
                    list(angles["right"]),
                    zero_angles,
                    tol=TuyaRobotBase.angle_tolerance,
                    name="右臂回零角度",
                )
            else:
                assert isinstance(angles, (list, tuple)) and len(angles) == 8
                assert_almost_equal(
                    list(angles),
                    zero_angles,
                    tol=TuyaRobotBase.angle_tolerance,
                    name=f"{target_name}回零角度",
                )
    finally:
        with allure.step("先切换双臂插补模式再回零，避免刷新模式阻塞清理"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
