# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.command_result import CommandResult
from pytuyarobot.validation import (
    TuyaRobotDualArmDataException,
    TuyaRobotSingleArmDataException,
)
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "upper_jog_coord",
    required_columns=("title", "api", "target", "coord_id", "direction", "speed", "status_code", "message", "expect_data", "test_type"),
)
manual_cases = [case for case in cases if case["test_type"] == "manual"]
unsupported_cases = [case for case in cases if case["test_type"] == "unsupported"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("坐标 Jog 全部用例结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.go_zero()


@allure.feature("笛卡尔坐标连续 Jog 运动")
@allure.story("单臂六轴和双臂Z轴按实机结束态断言")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_upper_jog_coord(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    coord_id = int(case["coord_id"])
    direction = int(case["direction"])
    speed = int(case["speed"])
    expect_data = case["expect_data"]
    success_return = expect_data is not None and str(expect_data).strip() != ""

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
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
        with allure.step(f"调用{target_name} upper_jog_coord 接口持续运动"):
            result = target_device.upper_jog_coord(coord_id, direction, speed, _async=False)
            logger.debug(f"接口 upper_jog_coord 返回：{result}")
        if success_return:
            expected = int(expect_data)
            with allure.step("断言接口返回业务值"):
                actual = device.result_data(result)
                allure.attach(str(expected), name="期望值", attachment_type=allure.attachment_type.TEXT)
                allure.attach(str(actual), name="实际值", attachment_type=allure.attachment_type.TEXT)
                assert actual == expected
        else:
            expected_status = int(case["status_code"])
            expected_message = str(case["message"])
            with allure.step("断言 Jog 运动以失败 CommandResult 结束"):
                assert isinstance(result, CommandResult), f"失败结束时应返回 CommandResult，实际: {result!r}"
                allure.attach(str(expected_status), name="期望状态码", attachment_type=allure.attachment_type.TEXT)
                allure.attach(str(result.status_code), name="实际状态码", attachment_type=allure.attachment_type.TEXT)
                allure.attach(expected_message, name="期望错误信息", attachment_type=allure.attachment_type.TEXT)
                allure.attach(result.message, name="实际错误信息", attachment_type=allure.attachment_type.TEXT)
                assert result.ok is False
                assert result.status_code == expected_status
                assert expected_message in result.message
            with allure.step("等待运动停止并读取结束时的实际坐标"):
                device.wait_upper(timeout=30)
                actual_coords = device.result_data(target_device.get_upper_coords())
                if target == "both":
                    assert isinstance(actual_coords, dict) and set(actual_coords) >= {"left", "right"}
                    assert all(isinstance(actual_coords[side], (list, tuple)) and len(actual_coords[side]) == 6 for side in ("left", "right"))
                else:
                    assert isinstance(actual_coords, (list, tuple)) and len(actual_coords) == 6
                allure.attach(str(actual_coords), name="结束时的实际坐标", attachment_type=allure.attachment_type.TEXT)
    finally:
        with allure.step("在用例结束后回到双臂零位"):
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("笛卡尔坐标连续 Jog 运动")
@allure.story("刷新模式不支持坐标 Jog")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", unsupported_cases, ids=lambda c: c["title"])
def test_upper_jog_coord_refresh_mode_unsupported(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected_message = str(case["message"])

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'coord_id:{case["coord_id"]}')
    logger.debug(f'direction:{case["direction"]}')
    logger.debug(f'speed:{case["speed"]}')

    with allure.step("先设置双臂插补模式并将目标单臂移动到坐标初始点位"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.move_to_coord_initial_pose(target)
    try:
        with allure.step(f"设置{target_name}为刷新模式"):
            assert device.result_data(target_device.set_upper_fresh_mode(1)) == 1
        with allure.step("刷新模式下显式启用默认异步状态"):
            assert upper_body.set_upper_motion_async(True) is True
        with allure.step(f"刷新模式下调用{target_name} upper_jog_coord 接口"):
            result = target_device.upper_jog_coord(case["coord_id"], case["direction"], case["speed"], _async=True)
            logger.debug(f"接口 upper_jog_coord 返回：{result}")
        with allure.step("断言刷新模式不支持坐标 Jog"):
            assert isinstance(result, CommandResult), f"刷新模式 Jog 应返回 CommandResult，实际: {result!r}"
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


@allure.feature("笛卡尔坐标连续 Jog 运动")
@allure.story("非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_upper_jog_coord_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected_exception = TuyaRobotDualArmDataException if target == "both" else TuyaRobotSingleArmDataException

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'coord_id:{case["coord_id"]}')
    logger.debug(f'direction:{case["direction"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(expected_exception) as exc:
        with allure.step(f"调用{target_name} upper_jog_coord 接口并验证非法参数"):
            target_device.upper_jog_coord(case["coord_id"], case["direction"], case["speed"])
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
