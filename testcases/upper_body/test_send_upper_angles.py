# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "send_upper_angles",
    required_columns=("title", "api", "target", "left_j1", "left_j2", "left_j3", "left_j4", "left_j5", "left_j6", "left_j7", "left_j8", "left_arm_speed", "left_gripper_speed", "right_j1", "right_j2", "right_j3", "right_j4", "right_j5", "right_j6", "right_j7", "right_j8", "right_arm_speed", "right_gripper_speed", "fresh_mode", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("全关节运动用例结束后恢复双臂插补模式"):
        result = upper_body.set_upper_fresh_mode(0)
        response = device.result_data(result)
        assert response == 1, f"恢复双臂插补模式失败，实际返回：{response}"


@allure.feature("全关节角度运动")
@allure.story("单臂和双臂全关节运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_send_upper_angles(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    fresh_mode = int(case["fresh_mode"])
    mode_name = "刷新模式" if fresh_mode == 1 else "插补模式"
    left_values = [case[f"left_j{joint_id}"] for joint_id in range(1, 9)]
    right_values = [case[f"right_j{joint_id}"] for joint_id in range(1, 9)]
    left_angles = None if any(value is None or value == "" for value in left_values) else [float(value) for value in left_values]
    right_angles = None if any(value is None or value == "" for value in right_values) else [float(value) for value in right_values]
    if target == "left" and left_angles is None:
        pytest.skip("左臂安全完整目标姿态尚未确认，目标角度按方案留空")
    if target == "right" and right_angles is None:
        pytest.skip("右臂安全完整目标姿态尚未确认，目标角度按方案留空")
    if target == "both" and (left_angles is None or right_angles is None):
        pytest.skip("双臂安全完整目标姿态尚未确认，目标角度按方案留空")
    expected = case["expect_data"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"fresh_mode:{fresh_mode}")
    logger.debug(f"left_angles:{left_angles}")
    logger.debug(f"right_angles:{right_angles}")
    logger.debug(f'left_arm_speed:{case["left_arm_speed"]}')
    logger.debug(f'left_gripper_speed:{case["left_gripper_speed"]}')
    logger.debug(f'right_arm_speed:{case["right_arm_speed"]}')
    logger.debug(f'right_gripper_speed:{case["right_gripper_speed"]}')

    with allure.step("读取运动前双臂角度"):
        original = device.result_data(upper_body.get_upper_angles())
        assert isinstance(original, dict) and set(original) >= {"left", "right"}
    with allure.step("读取运动前双臂刷新模式"):
        original_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original_modes, (list, tuple)) and len(original_modes) == 2
    with allure.step("读取运动前默认异步状态"):
        original_motion_async = upper_body.get_upper_motion_async()
        assert isinstance(original_motion_async, bool)
    try:
        with allure.step(f"设置{target_name}为{mode_name}"):
            if target == "left":
                mode_result = left_arm.set_upper_fresh_mode(fresh_mode)
            elif target == "right":
                mode_result = right_arm.set_upper_fresh_mode(fresh_mode)
            else:
                mode_result = upper_body.set_upper_fresh_mode(fresh_mode)
            mode_response = device.result_data(mode_result)
            assert mode_response == 1, f"{target_name}模式设置失败，实际返回：{mode_response}"

        with allure.step(f"回读并断言{target_name}运动模式"):
            actual_modes = device.result_data(upper_body.get_upper_fresh_mode())
            assert isinstance(actual_modes, (list, tuple)) and len(actual_modes) == 2
            allure.attach(str(fresh_mode), name="期望模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual_modes), name="双臂实际模式", attachment_type=allure.attachment_type.TEXT)
            if target in ("left", "both"):
                assert actual_modes[0] == fresh_mode, f"左臂模式不一致，期望：{fresh_mode}，实际：{actual_modes[0]}"
            if target in ("right", "both"):
                assert actual_modes[1] == fresh_mode, f"右臂模式不一致，期望：{fresh_mode}，实际：{actual_modes[1]}"

        with allure.step(f"设置{mode_name}对应的默认异步状态"):
            expected_motion_async = fresh_mode == 1
            actual_motion_async = upper_body.set_upper_motion_async(expected_motion_async)
            assert actual_motion_async is expected_motion_async

        with allure.step(f"调用{target_name} send_upper_angles 接口"):
            if target == "left":
                result = left_arm.send_upper_angles(left_angles, case["left_arm_speed"], case["left_gripper_speed"])
            elif target == "right":
                result = right_arm.send_upper_angles(right_angles, case["right_arm_speed"], case["right_gripper_speed"])
            else:
                result = upper_body.send_upper_angles(left_angles, case["left_arm_speed"], case["left_gripper_speed"], right_angles, case["right_arm_speed"], case["right_gripper_speed"])
            actual_result = device.result_data(result)
        with allure.step("断言运动接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual_result), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual_result == expected
        with allure.step("等待运动完成并断言目标关节角度"):
            device.wait_upper(timeout=30)
            if target == "left":
                actual_angles = device.result_data(left_arm.get_upper_angles())
                assert_almost_equal(list(actual_angles), left_angles, tol=TuyaRobotBase.angle_tolerance, name="左臂全关节运动")
            elif target == "right":
                actual_angles = device.result_data(right_arm.get_upper_angles())
                assert_almost_equal(list(actual_angles), right_angles, tol=TuyaRobotBase.angle_tolerance, name="右臂全关节运动")
            else:
                actual_angles = device.result_data(upper_body.get_upper_angles())
                assert_almost_equal(list(actual_angles["left"]), left_angles, tol=TuyaRobotBase.angle_tolerance, name="左臂全关节运动")
                assert_almost_equal(list(actual_angles["right"]), right_angles, tol=TuyaRobotBase.angle_tolerance, name="右臂全关节运动")
    finally:
        with allure.step("恢复左右臂原始角度"):
            device.result_data(left_arm.send_upper_angles(original["left"], TuyaRobotBase.speed, TuyaRobotBase.speed))
            device.result_data(right_arm.send_upper_angles(original["right"], TuyaRobotBase.speed, TuyaRobotBase.speed))
            device.wait_upper(timeout=30)
        with allure.step("恢复左右臂原始刷新模式"):
            left_mode_result = left_arm.set_upper_fresh_mode(int(original_modes[0]))
            right_mode_result = right_arm.set_upper_fresh_mode(int(original_modes[1]))
            assert device.result_data(left_mode_result) == 1
            assert device.result_data(right_mode_result) == 1
        with allure.step("恢复运动前默认异步状态"):
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")


@allure.feature("全关节角度运动")
@allure.story("双臂全关节非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_send_upper_angles_exception(upper_body, case):
    title = case["title"]
    left_angles = [case[f"left_j{joint_id}"] for joint_id in range(1, 9)]
    right_angles = [case[f"right_j{joint_id}"] for joint_id in range(1, 9)]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug("target:both")
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step("调用双臂 send_upper_angles 接口并验证非法参数"):
            upper_body.send_upper_angles(left_angles, case["left_arm_speed"], case["left_gripper_speed"], right_angles, case["right_arm_speed"], case["right_gripper_speed"])
    logger.info("✅ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
