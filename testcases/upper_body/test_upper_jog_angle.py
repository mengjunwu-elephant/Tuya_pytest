# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import (
    TuyaRobotDualArmDataException,
    TuyaRobotSingleArmDataException,
)
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "upper_jog_angle",
    required_columns=("title", "api", "target", "joint_id", "direction", "speed", "target_limit", "expect_data", "test_type"),
)
manual_cases = [case for case in cases if case["test_type"] == "manual"]
unsupported_cases = [case for case in cases if case["test_type"] == "unsupported"]
exception_cases = [case for case in cases if case["test_type"] == "exception" and case["joint_id"] != 0]
zero_joint_cases = [case for case in cases if case["test_type"] == "exception" and case["joint_id"] == 0]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("关节 Jog 全部用例结束后恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.go_zero()


@allure.feature("关节连续 Jog 运动")
@allure.story("单臂和双臂各关节正负向运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_upper_jog_angle(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    joint_id = int(case["joint_id"])
    direction = int(case["direction"])
    speed = int(case["speed"])
    target_limit = float(case["target_limit"])
    expected = case["expect_data"]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"direction:{direction}")
    logger.debug(f"speed:{speed}")

    with allure.step("设置双臂插补模式并在运动前回到零位"):
        mode_result = upper_body.set_upper_fresh_mode(0)
        assert device.result_data(mode_result) == 1
        actual_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(actual_modes, (list, tuple)) and len(actual_modes) == 2
        assert list(actual_modes) == [0, 0], f"双臂插补模式回读不一致，实际: {actual_modes}"
        device.go_zero()

    try:
        with allure.step(f"调用{target_name} upper_jog_angle 接口"):
            result = target_device.upper_jog_angle(joint_id, direction, speed, _async=True)
            actual_result = device.result_data(result)
            logger.debug(f"接口 upper_jog_angle 返回：{actual_result}")
            
        with allure.step("断言 Jog 接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual_result), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual_result == expected, f"响应不一致，期望: {expected}，实际: {actual_result}"

        with allure.step("等待 Jog 在软件限位停止并断言关节角度"):
            device.wait_upper(timeout=300)
            actual = device.result_data(upper_body.get_upper_angles())
            logger.debug(f"双臂实际角度：{actual}")

            assert isinstance(actual, dict) and set(actual) >= {"left", "right"}
            assert isinstance(actual["left"], (list, tuple)) and len(actual["left"]) == 8
            assert isinstance(actual["right"], (list, tuple)) and len(actual["right"]) == 8
            allure.attach(str(target_limit), name="期望软件限位", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="双臂实际角度", attachment_type=allure.attachment_type.TEXT)
            if target in ("left", "both"):
                assert_almost_equal(actual["left"][joint_id - 1], target_limit, tol=TuyaRobotBase.angle_tolerance, name=f"左臂J{joint_id} Jog运动")
            if target in ("right", "both"):
                assert_almost_equal(actual["right"][joint_id - 1], target_limit, tol=TuyaRobotBase.angle_tolerance, name=f"右臂J{joint_id} Jog运动")
    finally:
        with allure.step("在用例结束后回到双臂零位"):
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("关节连续 Jog 运动")
@allure.story("刷新模式不支持 Jog 运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", unsupported_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_refresh_mode_unsupported(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected = case["expect_data"]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'direction:{case["direction"]}')
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
        with allure.step(f"刷新模式下调用{target_name} upper_jog_angle 接口"):
            result = target_device.upper_jog_angle(case["joint_id"], case["direction"], case["speed"], _async=True)
            actual_result = device.result_data(result)
            logger.debug(f"接口 upper_jog_angle 返回：{actual_result}")
        with allure.step("断言刷新模式不支持 Jog 运动"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual_result), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual_result == expected, f"响应不一致，期望: {expected}，实际: {actual_result}"
    finally:
        with allure.step("恢复双臂插补模式并回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            device.go_zero()

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("关节连续 Jog 运动")
@allure.story("非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    expected_exception = TuyaRobotDualArmDataException if target == "both" else TuyaRobotSingleArmDataException

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'direction:{case["direction"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(expected_exception) as exc:
        with allure.step(f"调用{target_name} upper_jog_angle 接口并验证非法参数"):
            target_device.upper_jog_angle(case["joint_id"], case["direction"], case["speed"])
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("关节连续 Jog 运动")
@allure.story("关节ID为零异常")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", zero_joint_cases, ids=lambda c: c["title"])
def test_upper_jog_angle_joint_zero_exception(upper_body, left_arm, right_arm, case):
    """记录当前 SDK 将 joint_id=0 统一归类为双臂参数异常的实际契约。"""
    title = case["title"]
    target = str(case["target"]).lower()
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'direction:{case["direction"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step(f"调用{target_name} upper_jog_angle 接口并验证 joint_id=0"):
            target_device.upper_jog_angle(case["joint_id"], case["direction"], case["speed"])
    logger.info("✓ joint_id=0 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
