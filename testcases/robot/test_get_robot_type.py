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
@pytest.mark.parametrize('case', [case for case in cases if case['test_type'] == 'normal'], ids=lambda case: case['title'])
def test_get_robot_type(robot, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug('test_api: %s', case['api'])
    with allure.step('获取机器人类型'):
        response = robot.get_robot_type()
        logger.debug('接口 get_robot_type 返回：%r', response)
    assert isinstance(response, type(case['expect_data'])), (
        f'返回类型错误，期望 {type(case["expect_data"]).__name__}，'
        f'实际为 {type(response).__name__}'
    )
    assert response == case['expect_data']
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
