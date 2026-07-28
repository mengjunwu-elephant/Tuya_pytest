# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_motor_acc')

@allure.feature('底盘')
@allure.story('底盘接口验证：get_agv_motor_acc')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_agv_motor_acc(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'device_id:{case["device_id"]}')
    with allure.step('调用 get_agv_motor_acc 接口'):
        value = chassis.get_agv_motor_acc(case['device_id'])
        logger.debug(f"接口 get_agv_motor_acc 返回：{value}")
    with allure.step("断言接口返回结果"):
        assert isinstance(value, int) and (not isinstance(value, bool)), f'返回类型错误，期望 int，实际为 {type(value).__name__}: {value!r}'
    with allure.step("断言接口返回结果"):
        assert 0 <= value <= 32767
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
