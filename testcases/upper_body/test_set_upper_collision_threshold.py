# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotSingleArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "set_upper_collision_threshold", required_columns=("title", "api", "target", "joint_id", "threshold", "expect_data", "test_type"))
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身碰撞参数")
@allure.story("设置碰撞阈值")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_collision_threshold(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = case["target"]
    expected = case["expect_data"]
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'target:{case["target"]}, joint_id:{case["joint_id"]}, threshold:{case["threshold"]}')
    with allure.step("读取左右臂原始碰撞阈值"):
        original_left = list(device.result_data(left_arm.get_upper_collision_threshold()))
        original_right = list(device.result_data(right_arm.get_upper_collision_threshold()))
        assert len(original_left) == 7
        assert len(original_right) == 7
    try:
        with allure.step(f"调用{target_name} set_upper_collision_threshold 接口"):
            actual = device.result_data(target_device.set_upper_collision_threshold(case["joint_id"], case["threshold"]))
        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
        with allure.step("分别回读左右臂目标关节碰撞阈值"):
            current_left = list(device.result_data(left_arm.get_upper_collision_threshold()))
            current_right = list(device.result_data(right_arm.get_upper_collision_threshold()))
            index = case["joint_id"] - 1
            assert current_left[index] == (case["threshold"] if target in ("left", "both") else original_left[index])
            assert current_right[index] == (case["threshold"] if target in ("right", "both") else original_right[index])
    finally:
        with allure.step("分别恢复左右臂原始碰撞阈值"):
            for joint_id, value in enumerate(original_left, 1):
                device.result_data(left_arm.set_upper_collision_threshold(joint_id, value))
            for joint_id, value in enumerate(original_right, 1):
                device.result_data(right_arm.set_upper_collision_threshold(joint_id, value))
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")


@allure.feature("上半身碰撞参数")
@allure.story("验证碰撞阈值非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_upper_collision_threshold_exception(upper_body, left_arm, right_arm, case):
    title = case["title"]
    target = case["target"]
    target_device = {"left": left_arm, "right": right_arm, "both": upper_body}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'target:{target}, joint_id:{case["joint_id"]}, threshold:{case["threshold"]}')
    with pytest.raises(TuyaRobotSingleArmDataException) as exc:
        with allure.step("调用 set_upper_collision_threshold 校验非法参数"):
            target_device.set_upper_collision_threshold(case["joint_id"], case["threshold"])
    logger.info("✅ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
