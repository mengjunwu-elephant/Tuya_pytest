# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "send_upper_coord",
    required_columns=("title", "api", "arm_side", "coord_id", "value", "speed", "fresh_mode", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, robot):
    yield
    with allure.step("send_upper_coord 全部用例结束后恢复双臂插补模式"):
        result = robot.set_upper_fresh_mode(0)
        response = device.result_data(result)
        assert response == 1, f"恢复双臂插补模式失败，实际返回: {response}"


@allure.feature("单臂单坐标轴运动")
@allure.story("刷新与插补模式下各坐标轴正负运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_send_upper_coord(device, robot, upper_body, case):
    title = case["title"]
    arm_side = str(case["arm_side"]).lower()
    arm_name = "左臂" if arm_side == "left" else "右臂"
    arm_index = 0 if arm_side == "left" else 1
    arm = robot.left_arm if arm_side == "left" else robot.right_arm
    coord_id = int(case["coord_id"])
    value = float(case["value"])
    speed = int(case["speed"])
    fresh_mode = int(case["fresh_mode"])
    mode_name = "刷新模式" if fresh_mode == 1 else "插补模式"
    expected = case["expect_data"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"arm_side:{arm_side}")
    logger.debug(f"fresh_mode:{fresh_mode}")
    logger.debug(f"coord_id:{coord_id}")
    logger.debug(f"value:{value}")
    logger.debug(f"speed:{speed}")

    with allure.step("读取运动前双臂刷新模式和默认异步状态"):
        original_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original_modes, (list, tuple)) and len(original_modes) == 2
        original_motion_async = upper_body.get_upper_motion_async()
        assert isinstance(original_motion_async, bool)
    try:
        with allure.step("双臂移动到坐标运动初始关节姿态"):
            initial_actual = device.move_to_coord_initial_pose()
            allure.attach(
                str(TuyaRobotBase.COORD_MOTION_INITIAL_COORDS),
                name="期望初始坐标",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(
                str(initial_actual),
                name="实际初始坐标",
                attachment_type=allure.attachment_type.TEXT,
            )

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

        with allure.step(f"设置{mode_name}对应的默认异步状态"):
            expected_motion_async = fresh_mode == 1
            actual_motion_async = upper_body.set_upper_motion_async(expected_motion_async)
            assert actual_motion_async is expected_motion_async

        with allure.step(f"{arm_name}调用 {case['api']} 接口"):
            result = arm.send_upper_coord(coord_id, value, speed)
            logger.debug(f"接口返回：{result}")

        with allure.step("断言接口返回值"):
            response = device.result_data(result)
            allure.attach(str(expected), name="期望返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(response), name="实际返回值", attachment_type=allure.attachment_type.TEXT)
            assert expected == response, f"响应不一致，期望: {expected}，实际: {response}"

        with allure.step(f"等待{arm_name}运动完成并读取实际坐标"):
            device.wait_upper(timeout=30)
            actual = device.result_data(arm.get_upper_coords())
            assert isinstance(actual, (list, tuple)) and len(actual) == 6

        with allure.step(f"断言{arm_name}目标坐标轴到位"):
            allure.attach(str(value), name="期望坐标", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name=f"{arm_name}实际坐标", attachment_type=allure.attachment_type.TEXT)
            assert_almost_equal(
                actual[coord_id - 1],
                value,
                tol=TuyaRobotBase.coord_tolerance,
                name=f"{arm_name}坐标轴{coord_id}{mode_name}运动",
            )
    finally:
        with allure.step("回零前恢复双臂插补模式和默认同步状态"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
        with allure.step("当前坐标轴用例结束后双臂回零"):
            device.go_zero()
        with allure.step("恢复运动前双臂刷新模式和默认异步状态"):
            assert device.result_data(robot.left_arm.set_upper_fresh_mode(int(original_modes[0]))) == 1
            assert device.result_data(robot.right_arm.set_upper_fresh_mode(int(original_modes[1]))) == 1
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("单臂单坐标轴运动")
@allure.story("非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_send_upper_coord_exception(robot, case):
    title = case["title"]
    arm_side = str(case["arm_side"]).lower()
    arm_name = "左臂" if arm_side == "left" else "右臂"
    arm = robot.left_arm if arm_side == "left" else robot.right_arm
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"arm_side:{arm_side}")
    logger.debug(f'coord_id:{case["coord_id"]}')
    logger.debug(f'value:{case["value"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step(f"{arm_name}调用 {case['api']} 接口并验证非法参数"):
            arm.send_upper_coord(case["coord_id"], case["value"], case["speed"])
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
