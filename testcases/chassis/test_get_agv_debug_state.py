# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_debug_state')

@allure.feature('Chassis')
@allure.story('get_agv_debug_state')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_agv_debug_state(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('调用 get_agv_debug_state 接口'):
        state = chassis.get_agv_debug_state()
        logger.debug(f"接口 get_agv_debug_state 返回：{state}")
    with allure.step("断言接口返回结果"):
        assert isinstance(state, int) and (not isinstance(state, bool)), f'返回类型错误，期望 int，实际为 {type(state).__name__}: {state!r}'
    with allure.step("断言接口返回结果"):
        assert 0 <= state <= 4
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
