# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, "upper_stop")


@allure.feature("上半身运动控制")
@allure.story("停止单臂和双臂运动")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_upper_stop(device, upper_body, left_arm, right_arm, case):
    title, target = case["title"], case["target"]
    expected, expected_state = case["expect_data"], case["expect_state"]
    target_device, target_name = {"left": (left_arm, "左臂"), "right": (right_arm, "右臂"), "both": (upper_body, "双臂")}[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    with allure.step(f"调用{target_name} upper_stop 接口"):
        actual = device.result_data(target_device.upper_stop())
    with allure.step("断言停止接口业务返回值"):
        allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
        assert actual == expected
    with allure.step(f"查询并断言{target_name}运动状态"):
        state = device.result_data(target_device.get_upper_is_moving())
        if target == "both":
            assert list(state) == [expected_state, expected_state]
        else:
            assert state == expected_state
    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
