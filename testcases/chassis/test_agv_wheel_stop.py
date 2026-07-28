# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.operator_input import prompt_continue
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
import time

cases = get_test_data_from_excel(TuyaRobotBase.CHASSIS_TEST_DATA_FILE, 'agv_wheel_stop')

@allure.feature('底盘')
@allure.story('底盘接口验证：agv_wheel_stop')
@pytest.mark.chassis
@pytest.mark.motion
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_agv_wheel_stop(chassis, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    logger.debug(f'test_api:{case["api"]}')
    logger.debug(f'duration:{case["duration"]}')
    logger.debug(f'forward_mps:{case["forward_mps"]}')
    with allure.step('检查底盘上电状态'):
        power_state = chassis.is_agv_powered_on()
        assert power_state == 0, f'底盘未处于正常上电状态: {power_state!r}'
    prompt_continue('确认底盘行驶路径无人、无障碍物，且急停可用。', title='轮毂停止确认')
    try:
        with allure.step('调用 agv_wheel_control 接口'):
            start_response = chassis.agv_wheel_control(case['forward_mps'], 0.0)
            assert TuyaRobotBase.result_data(start_response) == 1, f'轮毂控制接口业务返回错误: {start_response!r}'
        duration = float(case['duration'])
        assert 0 < duration <= 5, f'轮毂控制持续时间必须在 (0, 5] 秒内，实际为 {duration!r}'
        time.sleep(duration)
        with allure.step('调用 agv_wheel_stop 接口'):
            response = chassis.agv_wheel_stop()
            logger.debug(f"接口 agv_wheel_stop 返回：{response}")
        with allure.step("断言接口返回结果"):
            assert TuyaRobotBase.result_data(response) == 1, f'轮毂停止接口业务返回错误: {response!r}'
    finally:
        with allure.step('调用 agv_wheel_stop 接口'):
            cleanup_response = chassis.agv_wheel_stop()
            assert TuyaRobotBase.result_data(cleanup_response) == 1, f'轮毂停止接口业务返回错误: {cleanup_response!r}'
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
