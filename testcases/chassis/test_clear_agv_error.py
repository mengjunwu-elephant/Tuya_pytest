# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'clear_agv_error')

@allure.feature('Chassis')
@allure.story('clear_agv_error')
@pytest.mark.chassis
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_clear_agv_error(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 clear_agv_error 接口'):
        response = chassis.clear_agv_error(case['device_id'])
        logger.debug('接口 clear_agv_error 返回：%r', response)
    assert response is not None, '底盘清错接口未返回 ACK'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
