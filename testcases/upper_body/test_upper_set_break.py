# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "upper_set_break")


@allure.feature("上半身关节安全控制")
@allure.story("设置单臂和双臂关节抱闸")
@pytest.mark.upper_body
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_upper_set_break(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    expected = case["expect_data"]
    target_device, target_name = {"left": (left_arm, "左臂"), "right": (right_arm, "右臂"), "both": (upper_body, "双臂")}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')
    logger.debug(f'state:{case["state"]}')
    prompt_continue(case["manual_check"], title=f"{target_name}关节抱闸安全确认")
    try:
        with allure.step(f"调用{target_name} upper_set_break 接口"):
            actual = device.result_data(target_device.upper_set_break(case["joint_id"], case["state"]))
        with allure.step("断言关节抱闸接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
    finally:
        with allure.step(f"释放{target_name}关节抱闸并恢复使能"):
            device.result_data(target_device.upper_set_break(case["joint_id"], 0))
            device.result_data(target_device.set_upper_joint_enable(case["joint_id"], 1))
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
