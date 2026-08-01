# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from pytuyarobot.validation import TuyaRobotDualArmDataException
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "set_joint_max_angle",
    required_columns=("title", "api", "joint_id", "degree", "expect_data", "test_type"),
)
normal_cases = [case for case in cases if case["test_type"] == "normal"]
exception_cases = [case for case in cases if case["test_type"] == "exception"]


@pytest.fixture(scope="module", autouse=True)
def restore_soft_joint_limits(device, upper_body):
    yield
    with allure.step("关节最大角度设置全部用例结束后恢复J1到J7软件限位"):
        for joint_id, (soft_min, soft_max) in TuyaRobotBase.UPPER_BODY_JOINT_SOFT_LIMITS.items():
            assert device.result_data(upper_body.set_joint_min_angle(joint_id, soft_min)) == 1
            assert device.result_data(upper_body.set_joint_max_angle(joint_id, soft_max)) == 1


@allure.feature("上半身参数设置")
@allure.story("设置上半身关节最大角度")
@pytest.mark.upper_body
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", normal_cases, ids=lambda c: c["title"])
def test_set_joint_max_angle(device, upper_body, case):
    title = case["title"]
    joint_id = int(case["joint_id"])
    degree = float(case["degree"])
    expected = int(case["expect_data"])
    soft_min, soft_max = TuyaRobotBase.UPPER_BODY_JOINT_SOFT_LIMITS[joint_id]

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"degree:{degree}")

    try:
        with allure.step("调用 set_joint_max_angle 接口"):
            actual = device.result_data(upper_body.set_joint_max_angle(joint_id, degree))
            logger.debug(f"接口 set_joint_max_angle 返回：{actual}")

        with allure.step("断言设置接口业务返回值"):
            allure.attach(str(expected), name="期望业务返回值", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual), name="实际业务返回值", attachment_type=allure.attachment_type.TEXT)
            assert actual == expected

        with allure.step("回读并断言目标关节最大角度"):
            limits = device.result_data(upper_body.get_upper_joints_max_angle())
            assert isinstance(limits, (list, tuple)) and len(limits) == 8
            actual_degree = limits[joint_id - 1]
            allure.attach(str(degree), name="期望最大角度", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(actual_degree), name="实际最大角度", attachment_type=allure.attachment_type.TEXT)
            assert actual_degree == degree
    finally:
        with allure.step("恢复该关节为软件上下限"):
            assert device.result_data(upper_body.set_joint_min_angle(joint_id, soft_min)) == 1
            assert device.result_data(upper_body.set_joint_max_angle(joint_id, soft_max)) == 1

    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")


@allure.feature("上半身参数设置")
@allure.story("验证关节最大角度非法参数")
@pytest.mark.upper_body
@pytest.mark.parametrize("case", exception_cases, ids=lambda c: c["title"])
def test_set_joint_max_angle_exception(upper_body, case):
    title = case["title"]
    joint_id = int(case["joint_id"])
    degree = float(case["degree"])

    logger.info(f">>>>>>>>>>用例【{title}】开始测试<<<<<<<<<<")
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f"joint_id:{joint_id}")
    logger.debug(f"degree:{degree}")

    with pytest.raises(TuyaRobotDualArmDataException) as exc:
        with allure.step("调用 set_joint_max_angle 接口并验证非法参数"):
            upper_body.set_joint_max_angle(joint_id, degree)
    logger.info("✓ 异常断言通过，异常信息：%s", exc.value)
    logger.info(f"✓ 用例【{title}】测试通过")
    logger.info(f">>>>>>>>>>用例【{title}】测试完成<<<<<<<<<<")
