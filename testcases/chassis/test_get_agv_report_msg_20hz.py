# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_report_msg_20hz')

@allure.feature('Chassis')
@allure.story('get_agv_report_msg_20hz')
@pytest.mark.chassis
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_agv_report_msg_20hz(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_agv_report_msg_20hz 接口'):
        response_1 = chassis.get_agv_report_msg_20hz()
        logger.debug('接口 get_agv_report_msg_20hz 返回：%r', response_1)
    assert isinstance(response_1, dict), f'返回类型错误，期望 dict，实际为 {type(response_1).__name__}: {response_1!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
