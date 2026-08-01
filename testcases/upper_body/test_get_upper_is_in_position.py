# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "get_upper_is_in_position",
    required_columns=(
        "title",
        "api",
        "target",
        "mode",
        "axis",
        "offset",
        "expect_data",
        "test_type",
    ),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]

AXIS_INDEX = {"J1": 0, "X": 0, "RX": 3}


@pytest.fixture(scope="module", autouse=True)
def prepare_coord_initial_pose(device, upper_body):
    with allure.step("模块开始：设置插补模式并将双臂运动到坐标初始点位"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        actual_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(actual_modes, (list, tuple)) and len(actual_modes) == 2
        assert list(actual_modes) == [0, 0], f"双臂插补模式回读不一致，实际: {actual_modes}"
        initial_actual = device.move_to_coord_initial_pose()
        allure.attach(str(initial_actual), name="实际坐标初始点位", attachment_type=allure.attachment_type.TEXT)
    yield
    with allure.step("模块结束：恢复双臂插补模式并回零"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        device.go_zero()


@allure.feature("上半身状态与参数查询")
@allure.story("坐标初始点位下角度坐标到位边界")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_get_upper_is_in_position(device, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    mode = int(case["mode"])
    axis = str(case["axis"]).upper()
    offset = float(case["offset"])
    expected = int(case["expect_data"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
    }[target]
    axis_index = AXIS_INDEX[axis]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"mode:{mode}")
    logger.debug(f"axis:{axis}")
    logger.debug(f"offset:{offset}")

    with allure.step(f"读取{target_name}当前{'关节角度' if mode == 0 else '坐标'}并构造查询目标"):
        if mode == 0:
            baseline = list(device.result_data(target_device.get_upper_angles()))
            assert len(baseline) == 8, f"关节角度长度错误：{baseline!r}"
            query_target = list(baseline)
            query_target[axis_index] = float(baseline[axis_index]) + offset
        else:
            baseline = list(device.result_data(target_device.get_upper_coords()))
            assert len(baseline) == 6, f"坐标长度错误：{baseline!r}"
            query_target = list(baseline)
            query_target[axis_index] = float(baseline[axis_index]) + offset
        allure.attach(str(baseline), name="基准值", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(query_target), name="查询目标", attachment_type=allure.attachment_type.TEXT)

    with allure.step(f"调用{target_name} get_upper_is_in_position 接口"):
        result = target_device.get_upper_is_in_position(mode, query_target)
        actual = device.result_data(result)
        logger.debug(f"接口 get_upper_is_in_position 返回：{actual}")

    with allure.step(f"断言{target_name}到位边界状态"):
        allure.attach(str(expected), name="期望到位状态", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(actual), name="实际到位状态", attachment_type=allure.attachment_type.TEXT)
        assert isinstance(actual, int) and not isinstance(actual, bool), (
            f"到位状态类型错误：{actual!r}"
        )
        assert actual == expected, f"到位状态不一致，期望: {expected}，实际: {actual}"

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("上半身状态与参数查询")
@allure.story("坐标初始点位下角度坐标到位超限")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_get_upper_is_in_position_exception(device, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    mode = int(case["mode"])
    axis = str(case["axis"]).upper()
    offset = float(case["offset"])
    expected = int(case["expect_data"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
    }[target]
    axis_index = AXIS_INDEX[axis]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"mode:{mode}")
    logger.debug(f"axis:{axis}")
    logger.debug(f"offset:{offset}")

    with allure.step(f"读取{target_name}当前{'关节角度' if mode == 0 else '坐标'}并构造查询目标"):
        if mode == 0:
            baseline = list(device.result_data(target_device.get_upper_angles()))
            assert len(baseline) == 8, f"关节角度长度错误：{baseline!r}"
            query_target = list(baseline)
            query_target[axis_index] = float(baseline[axis_index]) + offset
        else:
            baseline = list(device.result_data(target_device.get_upper_coords()))
            assert len(baseline) == 6, f"坐标长度错误：{baseline!r}"
            query_target = list(baseline)
            query_target[axis_index] = float(baseline[axis_index]) + offset
        allure.attach(str(baseline), name="基准值", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(query_target), name="查询目标", attachment_type=allure.attachment_type.TEXT)

    with allure.step(f"调用{target_name} get_upper_is_in_position 接口"):
        result = target_device.get_upper_is_in_position(mode, query_target)
        actual = device.result_data(result)
        logger.debug(f"接口 get_upper_is_in_position 返回：{actual}")

    with allure.step(f"断言{target_name}到位超限状态"):
        allure.attach(str(expected), name="期望到位状态", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(actual), name="实际到位状态", attachment_type=allure.attachment_type.TEXT)
        assert isinstance(actual, int) and not isinstance(actual, bool), (
            f"到位状态类型错误：{actual!r}"
        )
        assert actual == expected, f"到位状态不一致，期望: {expected}，实际: {actual}"

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
