# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.ROBOT_TEST_DATA_FILE, 'get_system_version')

@allure.feature('TuyaRobot 整机')
@allure.story('获取系统版本')
@pytest.mark.robot
@pytest.mark.smoke
@pytest.mark.parametrize('case', [case for case in cases if case['test_type'] == 'normal'], ids=lambda case: case['title'])
def test_get_system_version(robot, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_system_version 接口'):
        response = robot.get_system_version()
        logger.debug('接口 get_system_version 返回：%r', response)
    assert isinstance(response, (int, float)) and not isinstance(response, bool), (
        f'返回类型错误，期望数值，实际为 {type(response).__name__}: {response!r}'
    )
    assert float(response) == float(case['expect_data']), '版本号与 Excel 期望值不一致'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
