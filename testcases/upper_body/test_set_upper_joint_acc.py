# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_upper_joint_acc",
    required_columns=("title", "api", "target", "joint_id", "acc", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]

ACC_TOLERANCE = 0.001


@pytest.fixture(scope="module", autouse=True)
def restore_upper_interpolation_mode(device, upper_body):
    yield
    with allure.step("关节加速度设置全部用例结束后恢复双臂插补模式"):
        assert device.result_data(upper_body.set_upper_fresh_mode(0)) == 1
        assert upper_body.set_upper_motion_async(False) is False


@allure.feature("上半身参数设置")
@allure.story("刷新模式下设置关节加速度边界值")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_joint_acc(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = int(case["expect_data"])
    target = str(case["target"]).lower()
    joint_id = int(case["joint_id"])
    acc = float(case["acc"])
    joint_index = joint_id - 1
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"acc:{acc}")

    with allure.step("读取运动前双臂刷新模式和默认异步状态"):
        original_modes = device.result_data(upper_body.get_upper_fresh_mode())
        assert isinstance(original_modes, (list, tuple)) and len(original_modes) == 2
        original_motion_async = upper_body.get_upper_motion_async()
        assert isinstance(original_motion_async, bool)

    with allure.step("读取左右臂原始关节加速度"):
        original_left = list(device.result_data(left_arm.get_upper_joint_acc()))
        original_right = list(device.result_data(right_arm.get_upper_joint_acc()))
        assert len(original_left) == 7 and len(original_right) == 7

    try:
        with allure.step(f"设置{target_name}为刷新模式"):
            assert device.result_data(target_device.set_upper_fresh_mode(1)) == 1
            assert upper_body.set_upper_motion_async(True) is True

        with allure.step(f"调用{target_name} set_upper_joint_acc 接口"):
            result = target_device.set_upper_joint_acc(joint_id, acc)
            actual = device.result_data(result)
            logger.debug(f"接口 set_upper_joint_acc 返回：{actual}")

        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected

        with allure.step("分别回读左右臂关节加速度并断言目标关节"):
            current_left = list(device.result_data(left_arm.get_upper_joint_acc()))
            current_right = list(device.result_data(right_arm.get_upper_joint_acc()))
            allure.attach(str(acc), name="期望目标关节加速度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(current_left[joint_index]), name="左臂实际目标关节加速度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(current_right[joint_index]), name="右臂实际目标关节加速度", attachment_type=allure.attachment_type.TEXT)
            if target == "left":
                assert current_left[joint_index] == pytest.approx(acc, abs=ACC_TOLERANCE)
                assert current_right[joint_index] == pytest.approx(original_right[joint_index], abs=ACC_TOLERANCE)
            elif target == "right":
                assert current_left[joint_index] == pytest.approx(original_left[joint_index], abs=ACC_TOLERANCE)
                assert current_right[joint_index] == pytest.approx(acc, abs=ACC_TOLERANCE)
            else:
                assert current_left[joint_index] == pytest.approx(acc, abs=ACC_TOLERANCE)
                assert current_right[joint_index] == pytest.approx(acc, abs=ACC_TOLERANCE)
    finally:
        with allure.step("分别恢复左右臂原始关节加速度、刷新模式和默认异步状态"):
            assert device.result_data(left_arm.set_upper_fresh_mode(1)) == 1
            assert device.result_data(right_arm.set_upper_fresh_mode(1)) == 1
            assert upper_body.set_upper_motion_async(True) is True
            device.result_data(left_arm.set_upper_joint_acc(joint_id, float(original_left[joint_index])))
            device.result_data(right_arm.set_upper_joint_acc(joint_id, float(original_right[joint_index])))
            assert device.result_data(left_arm.set_upper_fresh_mode(int(original_modes[0]))) == 1
            assert device.result_data(right_arm.set_upper_fresh_mode(int(original_modes[1]))) == 1
            assert upper_body.set_upper_motion_async(original_motion_async) is original_motion_async

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("上半身参数设置")
@allure.story("验证关节加速度超限参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_upper_joint_acc_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = str(case["target"]).lower()
    joint_id = int(case["joint_id"])
    acc = float(case["acc"])
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"acc:{acc}")

    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step(f"调用{target_name} set_upper_joint_acc 接口并验证非法参数"):
            target_device.set_upper_joint_acc(joint_id, acc)
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
