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
    "send_upper_coords",
    required_columns=("title", "api", "target", *_COORD_COLUMNS, "left_speed", "right_speed", "fresh_mode", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("全坐标运动用例结束后恢复双臂插补模式"):
        result = upper_body.set_upper_fresh_mode(0)
        response = device.result_data(result)
        assert response == 1, f"恢复双臂插补模式失败，实际返回：{response}"


@allure.feature("全坐标运动")
@allure.story("单臂和双臂全坐标运动")
@pytest.mark.upper_body
@pytest.mark.motion
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_send_upper_coords(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    target_name = {"left": "左臂", "right": "右臂", "both": "双臂"}[target]
    fresh_mode = int(case["fresh_mode"])
    mode_name = "刷新模式" if fresh_mode == 1 else "插补模式"
    left_values = [case[f"left_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    right_values = [case[f"right_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    left_coords = None if any(value is None or value == "" for value in left_values) else [float(value) for value in left_values]
    right_coords = None if any(value is None or value == "" for value in right_values) else [float(value) for value in right_values]
    if target == "left" and left_coords is None:
        pytest.skip("左臂安全绝对坐标尚未确认，目标坐标按方案留空")
    if target == "right" and right_coords is None:
        pytest.skip("右臂安全绝对坐标尚未确认，目标坐标按方案留空")
    if target == "both" and (left_coords is None or right_coords is None):
        pytest.skip("双臂安全绝对坐标尚未确认，目标坐标按方案留空")
    expected = case["expect_data"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"fresh_mode:{fresh_mode}")
    logger.debug(f"left_coords:{left_coords}")
    logger.debug(f"right_coords:{right_coords}")
    logger.debug(f'left_speed:{case["left_speed"]}')
    logger.debug(f'right_speed:{case["right_speed"]}')

    with allure.step("进入并校验坐标运动初始姿态"):
        device.move_to_coord_initial_pose()
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

        with allure.step(f"调用{target_name} send_upper_coords 接口"):
            if target == "left":
                result = left_arm.send_upper_coords(left_coords, case["left_speed"])
            elif target == "right":
                result = right_arm.send_upper_coords(right_coords, case["right_speed"])
            else:
                result = upper_body.send_upper_coords(left_coords, case["left_speed"], right_coords, case["right_speed"])
            actual_result = device.result_data(result)
        with allure.step("断言运动接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual_result), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual_result == expected
        with allure.step("等待运动完成并断言目标坐标"):
            device.wait_upper(timeout=30)
            if target == "left":
                actual_coords = device.result_data(left_arm.get_upper_coords())
                assert_almost_equal(list(actual_coords), left_coords, tol=TuyaRobotBase.coord_tolerance, name="左臂全坐标运动")
            elif target == "right":
                actual_coords = device.result_data(right_arm.get_upper_coords())
                assert_almost_equal(list(actual_coords), right_coords, tol=TuyaRobotBase.coord_tolerance, name="右臂全坐标运动")
            else:
                actual_coords = device.result_data(upper_body.get_upper_coords())
                assert_almost_equal(list(actual_coords["left"]), left_coords, tol=TuyaRobotBase.coord_tolerance, name="左臂全坐标运动")
                assert_almost_equal(list(actual_coords["right"]), right_coords, tol=TuyaRobotBase.coord_tolerance, name="右臂全坐标运动")
    finally:
        with allure.step("回零前恢复双臂插补模式和默认同步状态"):
            assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
            assert upper_body.set_upper_motion_async(False) is False
        with allure.step("当前全坐标运动用例结束后双臂回零"):
            device.go_zero()
        with allure.step("恢复运动前双臂刷新模式和默认异步状态"):
            assert device.result_data(left_arm.set_upper_fresh_mode(int(original_modes[0]))) == 1
            assert device.result_data(right_arm.set_upper_fresh_mode(int(original_modes[1]))) == 1
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")


@allure.feature("全坐标运动")
@allure.story("双臂全坐标非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_send_upper_coords_exception(upper_body, case):
    title = case["title"]
    left_coords = [case[f"left_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    right_coords = [case[f"right_{axis}"] for axis in ("x", "y", "z", "rx", "ry", "rz")]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug("target:both")
    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step("调用双臂 send_upper_coords 接口并验证非法参数"):
            upper_body.send_upper_coords(left_coords, case["left_speed"], right_coords, case["right_speed"])
    logger.info("✅ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
