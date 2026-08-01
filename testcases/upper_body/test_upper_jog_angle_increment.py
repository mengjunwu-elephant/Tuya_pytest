# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.command_result import CommandResult
from pytuyarobot.validation import (
    TuyaRobotDualArmDataException,
    TuyaRobotSingleArmDataException,
)
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "upper_jog_angle_increment",
    required_columns=("title", "api", "target", "joint_id", "increment", "speed", "range_limit", "expect_data", "message", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
range_exception_cases = [case for case in cases if case["test_type"] == "range_exception"]
exception_cases = [case for case in cases if case["test_type"] == "exception" and case["joint_id"] != 0]
zero_joint_cases = [case for case in cases if case["test_type"] == "exception" and case["joint_id"] == 0]
unsupported_cases = [case for case in cases if case["test_type"] == "unsupported"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("关节步进运动全部用例结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.go_zero()


@allure.feature("关节角度步进运动")
@allure.story("单臂和双臂各关节步进30度")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_increment(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    joint_id = int(case["joint_id"])
    increment = float(case["increment"])
    speed = int(case["speed"])
    expected = case["expect_data"]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"increment:{increment}")
    logger.debug(f"speed:{speed}")

    with allure.step("设置双臂插补模式并在运动前回到零位"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        actual_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(actual_modes, (list, tuple)) and len(actual_modes) == 2
        assert list(actual_modes) == [0, 0], f"双臂插补模式回读不一致，实际: {actual_modes}"
        device.go_zero()

    try:
        with allure.step(f"调用{target_name} upper_jog_angle_increment 接口"):
            result = target_device.upper_jog_angle_increment(joint_id, increment, speed, _async=False)
            actual_result = device.result_data(result)
            logger.debug(f"接口 upper_jog_angle_increment 返回：{actual_result}")
        with allure.step("断言关节步进接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual_result), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual_result == expected, f"响应不一致，期望: {expected}，实际: {actual_result}"
        with allure.step("读取双臂角度并断言目标关节步进结果"):
            actual = device.result_data(upper_body.get_upper_angles())
            assert isinstance(actual, dict) and set(actual) >= {"left", "right"}
            assert isinstance(actual["left"], (list, tuple)) and len(actual["left"]) == 8
            assert isinstance(actual["right"], (list, tuple)) and len(actual["right"]) == 8
            allure.attach(str(increment), name="期望关节角度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="双臂实际角度", attachment_type=allure.attachment_type.TEXT)
            if target in ("left", "both"):
                assert_almost_equal(actual["left"][joint_id - 1], increment, tol=TuyaRobotBase.angle_tolerance, name=f"左臂J{joint_id}步进运动")
            if target in ("right", "both"):
                assert_almost_equal(actual["right"][joint_id - 1], increment, tol=TuyaRobotBase.angle_tolerance, name=f"右臂J{joint_id}步进运动")
    finally:
        with allure.step("在用例结束后回到双臂零位"):
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("关节角度步进运动")
@allure.story("超过关节完整行程的增量")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", range_exception_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_increment_range_exception(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected_exception = TuyaRobotDualArmDataException if target == "both" else TuyaRobotSingleArmDataException

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'increment:{case["increment"]}')
    logger.debug(f'speed:{case["speed"]}')
    logger.debug(f'range_limit:{case["range_limit"]}')

    with allure.step("设置双臂插补模式并在超限验证前回到零位"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.go_zero()
    try:
        with pytest.raises(expected_exception) as exc:
            with allure.step(f"调用{target_name} upper_jog_angle_increment 接口并验证增量超限"):
                target_device.upper_jog_angle_increment(case["joint_id"], case["increment"], case["speed"], _async=False)
        logger.info("✓ 增量超限异常断言通过，异常信息：%s", exc.value)
    finally:
        with allure.step("超限验证结束后回到双臂零位"):
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("关节角度步进运动")
@allure.story("刷新模式不支持关节步进")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", unsupported_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_increment_refresh_mode_unsupported(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected_message = str(case["message"])

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'increment:{case["increment"]}')
    logger.debug(f'speed:{case["speed"]}')

    with allure.step("先设置双臂插补模式并回到零位"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.go_zero()
    try:
        with allure.step(f"设置{target_name}为刷新模式"):
            assert device.result_data(target_device.set_upper_fresh_mode(1)) == 1
            actual_modes = device.result_data(upper_body.get_upper_fresh_mode())
            assert isinstance(actual_modes, (list, tuple)) and len(actual_modes) == 2
            assert actual_modes[0] == 1, f"左臂刷新模式回读不一致，实际: {actual_modes}"
        with allure.step("刷新模式下显式启用默认异步状态"):
            assert upper_body.set_upper_motion_async(True) is True
        with allure.step(f"刷新模式下调用{target_name} upper_jog_angle_increment 接口"):
            result = target_device.upper_jog_angle_increment(
                case["joint_id"], case["increment"], case["speed"], _async=True
            )
            logger.debug(f"接口 upper_jog_angle_increment 返回：{result}")
        with allure.step("断言刷新模式不支持关节步进"):
            assert isinstance(result, CommandResult), f"刷新模式步进应返回 CommandResult，实际: {result!r}"
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


@allure.feature("关节角度步进运动")
@allure.story("非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_increment_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected_exception = TuyaRobotDualArmDataException if target == "both" else TuyaRobotSingleArmDataException

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'increment:{case["increment"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(expected_exception) as exc:
        with allure.step(f"调用{target_name} upper_jog_angle_increment 接口并验证非法参数"):
            target_device.upper_jog_angle_increment(case["joint_id"], case["increment"], case["speed"])
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("关节角度步进运动")
@allure.story("关节ID为零异常")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", zero_joint_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_increment_joint_zero_exception(upper_body, left_arm, right_arm, case):
    """按当前 SDK 契约断言 joint_id=0：单臂 SingleArm，双臂 DualArm。"""
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected_exception = TuyaRobotDualArmDataException if target == "both" else TuyaRobotSingleArmDataException

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'increment:{case["increment"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(expected_exception) as exc:
        with allure.step(f"调用{target_name} upper_jog_angle_increment 接口并验证 joint_id=0"):
            target_device.upper_jog_angle_increment(case["joint_id"], case["increment"], case["speed"])
    logger.info("✓ joint_id=0 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
