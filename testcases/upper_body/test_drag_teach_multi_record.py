# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "drag_teach_multi_record")


@allure.feature("上半身拖动示教")
@allure.story("验证单臂和双臂 drag_teach_multi_record 接口")
@pytest.mark.upper_body
@pytest.mark.manual
@pytest.mark.motion
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_drag_teach_multi_record(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    expected = case["expect_data"]
    target_device, target_name = {"left": (left_arm, "左臂"), "right": (right_arm, "右臂"), "both": (upper_body, "双臂")}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'trajectory_id:{case["trajectory_id"]}')
    logger.debug(f'duration:{case["duration"]}')
    logger.debug(f'manual_check:{case["manual_check"]}')
    prompt_continue(case["manual_check"], title=f"{target_name}拖动示教安全确认")
    try:
        with allure.step(f"调用{target_name} drag_teach_multi_record 接口"):
            actual = device.result_data(target_device.drag_teach_multi_record(case["trajectory_id"]))
        with allure.step("断言接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected
        time.sleep(case["duration"])
    finally:
        with allure.step(f"暂停{target_name}示教录制"):
            device.result_data(target_device.upper_drag_teach_record_pause())
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
