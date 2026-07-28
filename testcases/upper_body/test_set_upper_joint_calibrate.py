# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "set_upper_joint_calibrate")


@allure.feature("上半身关节标定")
@allure.story("标定单臂和双臂关节零位")
@pytest.mark.upper_body
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_set_upper_joint_calibrate(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    expected = case["expect_data"]
    target_device, target_name = {"left": (left_arm, "左臂"), "right": (right_arm, "右臂"), "both": (upper_body, "双臂")}[target]
    joint_id = case["joint_id"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f"joint_id:{joint_id}")
    prompt_continue(case["release_check"], title=f"{target_name}零位标定：放松关节")
    try:
        with allure.step(f"失能并释放{target_name}目标关节"):
            device.result_data(target_device.set_upper_joint_enable(joint_id, 0))
            device.result_data(target_device.upper_set_break(joint_id, 1))
        prompt_continue(case["zero_check"], title=f"{target_name}零位标定：对准刻度线")
        with allure.step(f"恢复{target_name}目标关节抱闸和使能"):
            device.result_data(target_device.upper_set_break(joint_id, 0))
            device.result_data(target_device.set_upper_joint_enable(joint_id, 1))
        with allure.step(f"调用{target_name} set_upper_joint_calibrate 接口"):
            actual = device.result_data(target_device.set_upper_joint_calibrate(joint_id))
        with allure.step("断言关节标定接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
    finally:
        with allure.step(f"确保{target_name}目标关节抱闸和使能恢复"):
            device.result_data(target_device.upper_set_break(joint_id, 0))
            device.result_data(target_device.set_upper_joint_enable(joint_id, 1))
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
