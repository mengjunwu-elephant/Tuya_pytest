# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.assert_utils import assert_almost_equal
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_upper_world_reference",
    required_columns=("title", "api", "x", "y", "z", "rx", "ry", "rz", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@allure.feature("上半身参数设置")
@allure.story("设置双臂世界参考系")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_upper_world_reference(device, upper_body, case):
    title = case["title"]
    expected = int(case["expect_data"])
    setting_value = [float(case[axis]) for axis in ("x", "y", "z", "rx", "ry", "rz")]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    for axis, value in zip(("x", "y", "z", "rx", "ry", "rz"), setting_value):
        logger.debug(f"{axis}:{value}")

    with allure.step("读取原始世界参考系"):
        original = device.result_data(upper_body.get_upper_world_reference())
        original_coords = list(original["left"])
    try:
        with allure.step("调用双臂 set_upper_world_reference 接口"):
            actual = device.result_data(upper_body.set_upper_world_reference(setting_value))
            logger.debug(f"接口 set_upper_world_reference 返回：{actual}")

        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected

        with allure.step("回读并断言左右臂世界参考系"):
            current = device.result_data(upper_body.get_upper_world_reference())
            assert_almost_equal(
                current["left"],
                setting_value,
                tol=TuyaRobotBase.coord_tolerance,
                name="左臂世界参考系",
            )
            assert_almost_equal(
                current["right"],
                setting_value,
                tol=TuyaRobotBase.coord_tolerance,
                name="右臂世界参考系",
            )
    finally:
        with allure.step("恢复原始世界参考系"):
            device.result_data(upper_body.set_upper_world_reference(original_coords))

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("上半身参数设置")
@allure.story("验证世界参考系超软限位参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_upper_world_reference_exception(upper_body, case):
    title = case["title"]
    setting_value = [float(case[axis]) for axis in ("x", "y", "z", "rx", "ry", "rz")]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    for axis, value in zip(("x", "y", "z", "rx", "ry", "rz"), setting_value):
        logger.debug(f"{axis}:{value}")

    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step("调用双臂 set_upper_world_reference 接口并验证非法参数"):
            upper_body.set_upper_world_reference(setting_value)
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
