# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

_COORD_COLUMNS = tuple(f"{side}_{axis}" for side in ("left", "right") for axis in ("x", "y", "z", "rx", "ry", "rz"))
cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "write_upper_coords",
    required_columns=("title", "api", *_COORD_COLUMNS, "left_speed", "right_speed", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("全坐标写入运动")
@allure.story("双臂同时运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_write_upper_coords(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    left_values = [case[f"left_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    right_values = [case[f"right_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    left_coords = None if any(value is None or value == "" for value in left_values) else [float(value) for value in left_values]
    right_coords = None if any(value is None or value == "" for value in right_values) else [float(value) for value in right_values]
    if left_coords is None or right_coords is None:
        pytest.skip("双臂安全绝对坐标尚未经过实机确认，目标坐标按方案留空")
    left_speed, right_speed = int(case["left_speed"]), int(case["right_speed"])
    expected = case["expect_data"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"left_coords:{left_coords}")
    logger.debug(f"left_speed:{left_speed}")
    logger.debug(f"right_coords:{right_coords}")
    logger.debug(f"right_speed:{right_speed}")
    with allure.step("双臂移动到坐标运动初始关节姿态"):
        device.move_to_coord_initial_pose()
    with allure.step("读取运动前双臂坐标"):
        original = upper_body.get_upper_coords()
        assert isinstance(original, dict) and "left" in original and "right" in original
        assert len(original["left"]) == 6 and len(original["right"]) == 6
    try:
        with allure.step(f'调用 {case["api"]} 接口'):
            result = upper_body.write_upper_coords(left_coords, left_speed, right_coords, right_speed)
            logger.debug(f"接口返回：{result}")
        with allure.step("断言接口执行成功"):
            response = device.result_data(result)
            allure.attach(str(expected), name="期望返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(response), name="实际返回值", attachment_type=allure.attachment_type.TEXT)
            assert expected == response, f"响应不一致，期望: {expected}，实际: {response}"
        with allure.step("等待运动完成并断言左右臂坐标"):
            device.wait_upper(timeout=30)
            actual = upper_body.get_upper_coords()
            assert isinstance(actual, dict) and "left" in actual and "right" in actual
            assert len(actual["left"]) == 6 and len(actual["right"]) == 6
            allure.attach(str({"left": left_coords, "right": right_coords}), name="期望坐标", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际坐标", attachment_type=allure.attachment_type.TEXT)
            assert_almost_equal(list(actual["left"]), left_coords, tol=TuyaRobotBase.coord_tolerance, name="左臂全坐标运动")
            assert_almost_equal(list(actual["right"]), right_coords, tol=TuyaRobotBase.coord_tolerance, name="右臂全坐标运动")
    finally:
        with allure.step("恢复左右臂原始坐标"):
            left_arm.send_upper_coords(original["left"], TuyaRobotBase.speed)
            right_arm.send_upper_coords(original["right"], TuyaRobotBase.speed)
            device.wait_upper(timeout=30)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("全坐标写入运动")
@allure.story("非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_write_upper_coords_exception(upper_body, case):
    title = case["title"]
    left_values = [case[f"left_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    right_values = [case[f"right_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    left_coords = None if any(value is None or value == "" for value in left_values) else [float(value) for value in left_values]
    right_coords = None if any(value is None or value == "" for value in right_values) else [float(value) for value in right_values]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"left_coords:{left_coords}")
    logger.debug(f'left_speed:{case["left_speed"]}')
    logger.debug(f"right_coords:{right_coords}")
    logger.debug(f'right_speed:{case["right_speed"]}')
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step(f'调用 {case["api"]} 接口并验证非法参数'):
            upper_body.write_upper_coords(left_coords, case["left_speed"], right_coords, case["right_speed"])
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
