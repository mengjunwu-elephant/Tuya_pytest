# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_motors_current')

@allure.feature('Chassis')
@allure.story('get_agv_motors_current')
@pytest.mark.chassis
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_agv_motors_current(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_agv_motors_current 接口'):
        values = chassis.get_agv_motors_current()
        logger.debug('接口 get_agv_motors_current 返回：%r', values)
    assert isinstance(values, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(values).__name__}: {values!r}'
    assert values and all((isinstance(value, int) for value in values))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
