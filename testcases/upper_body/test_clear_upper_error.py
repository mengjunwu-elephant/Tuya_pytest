# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "clear_upper_error",
    required_columns=("title", "api", "target", "joint_id", "expect_data", "test_type"),
)


@allure.feature("上半身故障处理")
@allure.story("清除单臂和双臂错误")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_clear_upper_error(device, upper_body, left_arm, right_arm, case):
    title = case["title"]
    expected = case["expect_data"]
    target = case["target"]
    target_device, target_name = {
        "left": (left_arm, "左臂"),
        "right": (right_arm, "右臂"),
        "both": (upper_body, "双臂"),
    }[target]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"target:{target}")
    logger.debug(f'joint_id:{case["joint_id"]}')

    with allure.step(f"调用{target_name} clear_upper_error 接口"):
        actual = device.result_data(target_device.clear_upper_error(case["joint_id"]))
        logger.debug(f"接口 clear_upper_error 返回：{actual}")
    with allure.step("断言清错接口业务返回值"):
        allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
        assert actual == expected

    logger.info(f"✅ 用例【{title}】测试通过")
    logger.info(f"》》》》》用例【{title}】测试完成《《《《《")
