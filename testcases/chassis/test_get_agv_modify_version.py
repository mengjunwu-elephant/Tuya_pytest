# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_modify_version')

@allure.feature('Chassis')
@allure.story('get_agv_modify_version')
@pytest.mark.chassis
@pytest.mark.smoke
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_agv_modify_version(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_agv_modify_version 接口'):
        response_1 = chassis.get_agv_modify_version()
        logger.debug('接口 get_agv_modify_version 返回：%r', response_1)
    assert isinstance(response_1, (int, float)) and (not isinstance(response_1, bool)), f'返回类型错误，期望数值，实际为 {type(response_1).__name__}: {response_1!r}'
    assert float(response_1) == float(case['expect_data']), '版本号与 Excel 期望值不一致'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
