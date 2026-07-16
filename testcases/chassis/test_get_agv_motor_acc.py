# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_motor_acc')

@allure.feature('Chassis')
@allure.story('get_agv_motor_acc')
@pytest.mark.chassis
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_agv_motor_acc(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_agv_motor_acc 接口'):
        value = chassis.get_agv_motor_acc(case['device_id'])
        logger.debug('接口 get_agv_motor_acc 返回：%r', value)
    assert isinstance(value, int) and (not isinstance(value, bool)), f'返回类型错误，期望 int，实际为 {type(value).__name__}: {value!r}'
    assert 0 <= value <= 32767
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
