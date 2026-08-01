# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "send_upper_angle",
    required_columns=("title", "api", "arm_side", "joint_id", "angle", "speed", "fresh_mode", "expect_data", "test_type", "motion_mode"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal" and case["motion_mode"] == "separate"]
dual_arm_cases = [case for case in cases if case["test_type"] == "normal" and case["motion_mode"] == "dual"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]
manual_cases = [case for case in cases if case["test_type"] == "manual"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, robot):
    yield
    with allure.step("send_upper_angle 全部用例结束后恢复双臂插补模式"):
        result = robot.set_upper_fresh_mode(0)
        response = device.result_data(result)
        assert response == 1, f"恢复双臂插补模式失败，实际返回: {response}"


@allure.feature("单关节角度运动")
@allure.story("单臂刷新与插补模式运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_send_upper_angle(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    arm_side = str(case["arm_side"]).lower()
    arm_name = "左臂" if arm_side == "left" else "右臂"
    arm_index = 0 if arm_side == "left" else 1
    arm = left_arm if arm_side == "left" else right_arm
    joint_id = int(case["joint_id"])
    angle = float(case["angle"])
    speed = int(case["speed"])
    fresh_mode = int(case["fresh_mode"])
    mode_name = "刷新模式" if fresh_mode == 1 else "插补模式"
    expected = case["expect_data"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"arm_side:{arm_side}")
    logger.debug(f"fresh_mode:{fresh_mode}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"angle:{angle}")
    logger.debug(f"speed:{speed}")

    with allure.step("读取运动前左右臂刷新模式和默认异步模式"):
        original_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original_modes, (list, tuple)) and len(original_modes) == 2
        original_motion_async = upper_body.get_upper_motion_async()
        assert isinstance(original_motion_async, bool)
    try:
        with allure.step(f"设置{arm_name}为{mode_name}"):
            mode_result = arm.set_upper_fresh_mode(fresh_mode)
            mode_response = device.result_data(mode_result)
            assert mode_response == 1, f"{arm_name}模式设置失败，实际返回: {mode_response}"

        with allure.step(f"回读并断言{arm_name}运动模式"):
            modes = device.result_data(upper_body.get_upper_fresh_mode())
            assert isinstance(modes, (list, tuple)) and len(modes) == 2
            allure.attach(str(fresh_mode), name="期望模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(modes), name="双臂实际模式", attachment_type=allure.attachment_type.TEXT)
            assert modes[arm_index] == fresh_mode, f"{arm_name}模式不一致，期望: {fresh_mode}，实际: {modes[arm_index]}"

        with allure.step("按刷新模式设置默认异步运动并回读断言"):
            expected_motion_async = fresh_mode == 1
            if fresh_mode == 1:
                actual_motion_async = upper_body.set_upper_motion_async(True)
            else:
                actual_motion_async = upper_body.set_upper_motion_async(False)
            current_motion_async = upper_body.get_upper_motion_async()
            allure.attach(str(expected_motion_async), name="期望默认异步模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(current_motion_async), name="实际默认异步模式", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(actual_motion_async, bool)
            assert actual_motion_async is expected_motion_async
            assert current_motion_async is expected_motion_async

        with allure.step(f'{arm_name}调用 {case["api"]} 接口'):
            result = arm.send_upper_angle(joint_id, angle, speed)
            logger.debug(f"{arm_name}接口返回：{result}")

        with allure.step(f"断言{arm_name}接口执行成功"):
            response = device.result_data(result)
            allure.attach(str(expected), name="期望返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(response), name="实际返回值", attachment_type=allure.attachment_type.TEXT)
            assert expected == response, f"{arm_name}响应不一致，期望: {expected}，实际: {response}"

        with allure.step(f"等待{arm_name}运动完成并读取实际角度"):
            device.wait_upper(timeout=30)
            actual = upper_body.get_upper_angles()
            assert isinstance(actual, dict) and arm_side in actual
            assert len(actual[arm_side]) == 8

        with allure.step(f"断言{arm_name}目标关节到位"):
            allure.attach(str(angle), name="期望角度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual[arm_side]), name=f"{arm_name}实际角度", attachment_type=allure.attachment_type.TEXT)
            assert_almost_equal(actual[arm_side][joint_id - 1], angle, tol=TuyaRobotBase.angle_tolerance, name=f"{arm_name}J{joint_id}{mode_name}运动")
    finally:
        with allure.step("切回双臂插补模式后回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            device.go_zero()
        with allure.step("恢复左右臂原始刷新模式和默认异步模式"):
            assert device.result_data(left_arm.set_upper_fresh_mode(int(original_modes[0]))) == 1
            assert device.result_data(right_arm.set_upper_fresh_mode(int(original_modes[1]))) == 1
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("单关节角度运动")
@allure.story("双臂刷新与插补模式同时运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", dual_arm_cases, ids=lambda c: c["title"])
def test_send_upper_angle_dual_arm(device, robot, upper_body, case):
    title = case["title"]
    joint_id = int(case["joint_id"])
    angle = float(case["angle"])
    speed = int(case["speed"])
    fresh_mode = int(case["fresh_mode"])
    mode_name = "刷新模式" if fresh_mode == 1 else "插补模式"
    expected = case["expect_data"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"fresh_mode:{fresh_mode}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"angle:{angle}")
    logger.debug(f"speed:{speed}")

    with allure.step("读取运动前左右臂刷新模式和默认异步模式"):
        original_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original_modes, (list, tuple)) and len(original_modes) == 2
        original_motion_async = upper_body.get_upper_motion_async()
        assert isinstance(original_motion_async, bool)
    try:
        with allure.step(f"设置双臂为{mode_name}"):
            mode_result = robot.set_upper_fresh_mode(fresh_mode)
            mode_response = device.result_data(mode_result)
            assert mode_response == 1, f"双臂模式设置失败，实际返回: {mode_response}"

        with allure.step("回读并断言双臂运动模式"):
            modes = device.result_data(upper_body.get_upper_fresh_mode())
            assert isinstance(modes, (list, tuple)) and len(modes) == 2
            allure.attach(str([fresh_mode, fresh_mode]), name="期望模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(modes), name="实际模式", attachment_type=allure.attachment_type.TEXT)
            assert list(modes) == [fresh_mode, fresh_mode]

        with allure.step("按刷新模式设置默认异步运动并回读断言"):
            expected_motion_async = fresh_mode == 1
            if fresh_mode == 1:
                actual_motion_async = upper_body.set_upper_motion_async(True)
            else:
                actual_motion_async = upper_body.set_upper_motion_async(False)
            current_motion_async = upper_body.get_upper_motion_async()
            allure.attach(str(expected_motion_async), name="期望默认异步模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(current_motion_async), name="实际默认异步模式", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(actual_motion_async, bool)
            assert actual_motion_async is expected_motion_async
            assert current_motion_async is expected_motion_async

        with allure.step(f'调用 robot.{case["api"]} 接口设置双臂同时运动'):
            result = robot.send_upper_angle(joint_id, angle, speed)
            logger.debug(f"接口返回：{result}")

        with allure.step("断言接口返回值"):
            response = device.result_data(result)
            allure.attach(str(expected), name="期望返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(response), name="实际返回值", attachment_type=allure.attachment_type.TEXT)
            assert expected == response, f"响应不一致，期望: {expected}，实际: {response}"

        with allure.step("等待双臂运动完成并读取实际角度"):
            device.wait_upper(timeout=30)
            actual = upper_body.get_upper_angles()
            assert isinstance(actual, dict) and "left" in actual and "right" in actual
            assert len(actual["left"]) == 8 and len(actual["right"]) == 8

        with allure.step("断言双臂目标关节到位"):
            allure.attach(str(angle), name="期望角度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="双臂实际角度", attachment_type=allure.attachment_type.TEXT)
            assert_almost_equal(actual["left"][joint_id - 1], angle, tol=TuyaRobotBase.angle_tolerance, name=f"左臂J{joint_id}{mode_name}运动")
            assert_almost_equal(actual["right"][joint_id - 1], angle, tol=TuyaRobotBase.angle_tolerance, name=f"右臂J{joint_id}{mode_name}运动")
    finally:
        with allure.step("切回双臂插补模式后回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            device.go_zero()
        with allure.step("恢复左右臂原始刷新模式和默认异步模式"):
            assert device.result_data(robot.left_arm.set_upper_fresh_mode(int(original_modes[0]))) == 1
            assert device.result_data(robot.right_arm.set_upper_fresh_mode(int(original_modes[1]))) == 1
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("单关节角度运动")
@allure.story("非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_send_upper_angle_exception(upper_body, case):
    title = case["title"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'angle:{case["angle"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step(f'调用 {case["api"]} 接口并验证非法参数'):
            upper_body.send_upper_angle(case["joint_id"], case["angle"], case["speed"])
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("单关节角度运动")
@allure.story("单臂刷新与插补模式软件限位运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", manual_cases, ids=lambda c: c["title"])
def test_send_upper_angle_soft_limit(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    arm_side = str(case["arm_side"]).lower()
    arm_name = "左臂" if arm_side == "left" else "右臂"
    arm_index = 0 if arm_side == "left" else 1
    arm = left_arm if arm_side == "left" else right_arm
    joint_id = int(case["joint_id"])
    angle = float(case["angle"])
    speed = int(case["speed"])
    fresh_mode = int(case["fresh_mode"])
    mode_name = "刷新模式" if fresh_mode == 1 else "插补模式"
    expected = case["expect_data"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"arm_side:{arm_side}")
    logger.debug(f"fresh_mode:{fresh_mode}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"angle:{angle}")
    logger.debug(f"speed:{speed}")

    with allure.step("读取运动前左右臂刷新模式和默认异步模式"):
        original_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original_modes, (list, tuple)) and len(original_modes) == 2
        original_motion_async = upper_body.get_upper_motion_async()
        assert isinstance(original_motion_async, bool)
    try:
        with allure.step(f"设置{arm_name}为{mode_name}"):
            mode_result = arm.set_upper_fresh_mode(fresh_mode)
            mode_response = device.result_data(mode_result)
            assert mode_response == 1, f"{arm_name}模式设置失败，实际返回: {mode_response}"

        with allure.step(f"回读并断言{arm_name}运动模式"):
            modes = device.result_data(upper_body.get_upper_fresh_mode())
            assert isinstance(modes, (list, tuple)) and len(modes) == 2
            allure.attach(str(fresh_mode), name="期望模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(modes), name="双臂实际模式", attachment_type=allure.attachment_type.TEXT)
            assert modes[arm_index] == fresh_mode, f"{arm_name}模式不一致，期望: {fresh_mode}，实际: {modes[arm_index]}"

        with allure.step("按刷新模式设置默认异步运动并回读断言"):
            expected_motion_async = fresh_mode == 1
            if fresh_mode == 1:
                actual_motion_async = upper_body.set_upper_motion_async(True)
            else:
                actual_motion_async = upper_body.set_upper_motion_async(False)
            current_motion_async = upper_body.get_upper_motion_async()
            allure.attach(str(expected_motion_async), name="期望默认异步模式", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(current_motion_async), name="实际默认异步模式", attachment_type=allure.attachment_type.TEXT)
            assert isinstance(actual_motion_async, bool)
            assert actual_motion_async is expected_motion_async
            assert current_motion_async is expected_motion_async

        with allure.step(f'{arm_name}调用 {case["api"]} 接口'):
            result = arm.send_upper_angle(joint_id, angle, speed)
            logger.debug(f"{arm_name}接口返回：{result}")

        with allure.step(f"断言{arm_name}接口执行成功"):
            response = device.result_data(result)
            allure.attach(str(expected), name="期望返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(response), name="实际返回值", attachment_type=allure.attachment_type.TEXT)
            assert expected == response, f"{arm_name}响应不一致，期望: {expected}，实际: {response}"

        with allure.step(f"等待{arm_name}运动完成并读取实际角度"):
            device.wait_upper(timeout=30)
            actual = upper_body.get_upper_angles()
            assert isinstance(actual, dict) and arm_side in actual
            assert len(actual[arm_side]) == 8

        with allure.step(f"断言{arm_name}目标关节到位"):
            allure.attach(str(angle), name="期望角度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual[arm_side]), name=f"{arm_name}实际角度", attachment_type=allure.attachment_type.TEXT)
            assert_almost_equal(actual[arm_side][joint_id - 1], angle, tol=TuyaRobotBase.angle_tolerance, name=f"{arm_name}J{joint_id}{mode_name}软件限位运动")
    finally:
        with allure.step("切回双臂插补模式后回零"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            device.go_zero()
        with allure.step("恢复左右臂原始刷新模式和默认异步模式"):
            assert device.result_data(left_arm.set_upper_fresh_mode(int(original_modes[0]))) == 1
            assert device.result_data(right_arm.set_upper_fresh_mode(int(original_modes[1]))) == 1
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
