# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_robot_status')

@allure.feature('底盘')
@allure.story('底盘接口验证：get_agv_robot_status')
@pytest.mark.chassis
@pytest.mark.smoke
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_agv_robot_status(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('调用 get_agv_robot_status 接口'):
        status = chassis.get_agv_robot_status()
        logger.debug(f"接口 get_agv_robot_status 返回：{status}")
    with allure.step("断言接口返回结果"):
        assert isinstance(status, dict), f'返回类型错误，期望 dict，实际为 {type(status).__name__}: {status!r}'
    with allure.step("断言接口返回结果"):
        assert {'status', 'message', 'battery_voltage', 'battery_level'} <= set(status)
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
