# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_motors_temp')

@allure.feature('Chassis')
@allure.story('get_agv_motors_temp')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_agv_motors_temp(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('调用 get_agv_motors_temp 接口'):
        values = chassis.get_agv_motors_temp()
        logger.debug(f"接口 get_agv_motors_temp 返回：{values}")
    with allure.step("断言接口返回结果"):
        assert isinstance(values, dict), f'返回类型错误，期望 dict，实际为 {type(values).__name__}: {values!r}'
    response_1 = values['motor']
    with allure.step("断言接口返回结果"):
        assert isinstance(response_1, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(response_1).__name__}: {response_1!r}'
    response_2 = values['driver']
    with allure.step("断言接口返回结果"):
        assert isinstance(response_2, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(response_2).__name__}: {response_2!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
