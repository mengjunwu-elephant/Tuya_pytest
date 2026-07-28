# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_motors_loss_count')

@allure.feature('底盘')
@allure.story('底盘接口验证：get_agv_motors_loss_count')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_agv_motors_loss_count(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('调用 get_agv_motors_loss_count 接口'):
        values = chassis.get_agv_motors_loss_count()
        logger.debug(f"接口 get_agv_motors_loss_count 返回：{values}")
    with allure.step("断言接口返回结果"):
        assert isinstance(values, (list, tuple)), f'返回类型错误，期望 list/tuple，实际为 {type(values).__name__}: {values!r}'
    with allure.step("断言接口返回结果"):
        assert values and all((isinstance(value, int) and value >= 0 for value in values))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
