# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_joints_status')

@allure.feature('UpperBody')
@allure.story('get_upper_joints_status')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_joints_status(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_upper_joints_status 接口'):
        status = upper_body.get_upper_joints_status()
        logger.debug('接口 get_upper_joints_status 返回：%r', status)
    assert isinstance(status, dict), f'返回类型错误，期望 dict，实际为 {type(status).__name__}: {status!r}'
    assert 'left' in status and 'right' in status
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
