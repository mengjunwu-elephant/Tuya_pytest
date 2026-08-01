# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.command_result import CommandResult
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "clear_upper_error",
    required_columns=(
        "title",
        "api",
        "target",
        "joint_id",
        "coord_id",
        "direction",
        "speed",
        "status_code",
        "message",
        "expect_data",
        "test_type",
    ),
)
manual_cases = [case for case in cases if case["test_type"] == "manual"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("清错用例全部结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.go_zero()


@allure.feature("上半身故障处理")
@allure.story("Jog触发报错后清除错误")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_clear_upper_error(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    joint_id = int(case["joint_id"])
    coord_id = int(case["coord_id"])
    direction = int(case["direction"])
    speed = int(case["speed"])
    expected_status = int(case["status_code"])
    expected_message = str(case["message"])
    expected = int(case["expect_data"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"coord_id:{coord_id}")
    logger.debug(f"direction:{direction}")
    logger.debug(f"speed:{speed}")

    with allure.step("设置双臂插补模式并进入目标手臂坐标初始点位"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        actual_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(actual_modes, (list, tuple)) and len(actual_modes) == 2
        assert list(actual_modes) == [0, 0], f"双臂插补模式回读不一致，实际: {actual_modes}"
        initial_actual = device.move_to_coord_initial_pose(None if target == "both" else target)
        allure.attach(str(initial_actual), name="实际坐标初始点位", attachment_type=allure.attachment_type.TEXT)

    try:
        with allure.step(f"调用{target_name} upper_jog_coord 触发目标报错"):
            jog_result = target_device.upper_jog_coord(coord_id, direction, speed, _async=False)
            logger.debug(f"接口 upper_jog_coord 返回：{jog_result}")
            assert isinstance(jog_result, CommandResult), f"触发报错时应返回 CommandResult，实际: {jog_result!r}"
            allure.attach(str(expected_status), name="期望Jog状态码", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(jog_result.status_code), name="实际Jog状态码", attachment_type=allure.attachment_type.TEXT)
            allure.attach(expected_message, name="期望Jog错误信息", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(jog_result.message), name="实际Jog错误信息", attachment_type=allure.attachment_type.TEXT)
            assert jog_result.ok is False
            assert jog_result.status_code == expected_status
            assert expected_message in (jog_result.message or "")

        with allure.step(f"读取并断言{target_name}已报错"):
            error_status = device.result_data(target_device.get_upper_robot_status())
            logger.debug(f"接口 get_upper_robot_status 报错后返回：{error_status}")
            allure.attach(str(error_status), name="报错后状态", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert isinstance(error_status, dict), f"双臂状态应返回 dict，实际: {error_status!r}"
                assert set(error_status) >= {"left", "right"}
                has_error = False
                for side in ("left", "right"):
                    side_status = error_status[side]
                    if isinstance(side_status, dict) and (
                        "soft_error" in side_status or "motor_errors" in side_status
                    ):
                        has_error = True
                        break
                assert has_error, f"双臂应至少一侧包含 soft_error 或 motor_errors，实际: {error_status!r}"
            else:
                assert isinstance(error_status, dict), f"单臂报错状态应返回 dict，实际: {error_status!r}"
                assert ("soft_error" in error_status) or ("motor_errors" in error_status), (
                    f"单臂报错状态应包含 soft_error 或 motor_errors，实际: {error_status!r}"
                )

        with allure.step(f"调用{target_name} clear_upper_error 接口"):
            clear_result = target_device.clear_upper_error(joint_id)
            actual = device.result_data(clear_result)
            logger.debug(f"接口 clear_upper_error 返回：{actual}")

        with allure.step("断言清错接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected

        with allure.step(f"读取并断言{target_name}已无报错"):
            cleared_status = device.result_data(target_device.get_upper_robot_status())
            logger.debug(f"接口 get_upper_robot_status 清错后返回：{cleared_status}")
            allure.attach(str(cleared_status), name="清错后状态", attachment_type=allure.attachment_type.TEXT)
            if target == "both":
                assert isinstance(cleared_status, dict), f"双臂状态应返回 dict，实际: {cleared_status!r}"
                assert set(cleared_status) >= {"left", "right"}
                assert cleared_status["left"] == 0 and cleared_status["right"] == 0, (
                    f"清错后双臂应均为 0，实际: {cleared_status!r}"
                )
            else:
                assert cleared_status == 0, f"清错后单臂状态应为 0，实际: {cleared_status!r}"
    finally:
        with allure.step("在用例结束后回到双臂零位"):
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
