# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.ROBOT_TEST_DATA_FILE, 'get_robot_type')

@allure.feature('TuyaRobot 整机')
@allure.story('获取机器人类型')
@pytest.mark.robot
@pytest.mark.smoke
@pytest.mark.parametrize("case", [case for case in cases if case['test_type'] == 'normal'], ids=lambda c: c["title"])
def test_get_robot_type(robot, case):
    title = case['title']
    expected = case["expect_data"]
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug('test_api: %s', case['api'])
    with allure.step('获取机器人类型'):
        response = robot.get_robot_type()
        logger.debug(f"接口 get_robot_type 返回：{response}")
    with allure.step("断言接口返回结果"):
        allure.attach(str(expected), name="期望值", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(response), name="实际值", attachment_type=allure.attachment_type.TEXT)
        assert isinstance(response, type(expected)), (
            f'返回类型错误，期望 {type(expected).__name__}，'
            f'实际为 {type(response).__name__}'
        )
    with allure.step("断言接口返回结果"):
        assert response == expected
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
