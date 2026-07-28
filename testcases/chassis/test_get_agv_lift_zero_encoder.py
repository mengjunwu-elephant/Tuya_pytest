# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'get_agv_lift_zero_encoder')

@allure.feature('底盘')
@allure.story('底盘接口验证：get_agv_lift_zero_encoder')
@pytest.mark.chassis
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_get_agv_lift_zero_encoder(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    with allure.step('调用 get_agv_lift_zero_encoder 接口'):
        response_1 = chassis.get_agv_lift_zero_encoder()
        logger.debug(f"接口 get_agv_lift_zero_encoder 返回：{response_1}")
    with allure.step("断言接口返回结果"):
        assert isinstance(response_1, int) and (not isinstance(response_1, bool)), f'返回类型错误，期望 int，实际为 {type(response_1).__name__}: {response_1!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
