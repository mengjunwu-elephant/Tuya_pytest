# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import assert_almost_equal, logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "write_upper_coord",
    required_columns=("title", "api", "coord_id", "value", "speed", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("单坐标轴写入运动")
@allure.story("双臂同时运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_write_upper_coord(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    if case["value"] is None or case["value"] == "":
        pytest.skip("安全绝对坐标尚未经过实机确认，目标坐标按方案留空")
    coord_id, value, speed = int(case["coord_id"]), float(case["value"]), int(case["speed"])
    expected = case["expect_data"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"coord_id:{coord_id}")
    logger.debug(f"value:{value}")
    logger.debug(f"speed:{speed}")
    with allure.step("双臂移动到坐标运动初始关节姿态"):
        device.move_to_coord_initial_pose()
    with allure.step("读取运动前双臂坐标"):
        original = upper_body.get_upper_coords()
        assert isinstance(original, dict) and "left" in original and "right" in original
        assert len(original["left"]) == 6 and len(original["right"]) == 6
    try:
        with allure.step(f'调用 {case["api"]} 接口'):
            result = upper_body.write_upper_coord(coord_id, value, speed)
            logger.debug(f"接口返回：{result}")
        with allure.step("断言接口执行成功"):
            response = device.result_data(result)
            allure.attach(str(expected), name="期望返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(response), name="实际返回值", attachment_type=allure.attachment_type.TEXT)
            assert expected == response, f"响应不一致，期望: {expected}，实际: {response}"
        with allure.step("等待运动完成并断言左右臂目标坐标"):
            device.wait_upper(timeout=30)
            actual = upper_body.get_upper_coords()
            assert isinstance(actual, dict) and "left" in actual and "right" in actual
            assert len(actual["left"]) == 6 and len(actual["right"]) == 6
            allure.attach(str(value), name="期望坐标", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际坐标", attachment_type=allure.attachment_type.TEXT)
            assert_almost_equal(actual["left"][coord_id - 1], value, tol=TuyaRobotBase.coord_tolerance, name=f"左臂坐标轴{coord_id}运动")
            assert_almost_equal(actual["right"][coord_id - 1], value, tol=TuyaRobotBase.coord_tolerance, name=f"右臂坐标轴{coord_id}运动")
    finally:
        with allure.step("恢复左右臂原始坐标"):
            left_arm.send_upper_coords(original["left"], TuyaRobotBase.speed)
            right_arm.send_upper_coords(original["right"], TuyaRobotBase.speed)
            device.wait_upper(timeout=30)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("单坐标轴写入运动")
@allure.story("非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_write_upper_coord_exception(upper_body, case):
    title = case["title"]
    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'coord_id:{case["coord_id"]}')
    logger.debug(f'value:{case["value"]}')
    logger.debug(f'speed:{case["speed"]}')
    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step(f'调用 {case["api"]} 接口并验证非法参数'):
            upper_body.write_upper_coord(case["coord_id"], case["value"], case["speed"])
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
