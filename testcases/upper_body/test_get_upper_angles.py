# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_angles')

@allure.feature('UpperBody')
@allure.story('get_upper_angles')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_angles(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_upper_angles 接口'):
        angles = upper_body.get_upper_angles()
        logger.debug('接口 get_upper_angles 返回：%r', angles)
    assert isinstance(angles, dict), f'返回类型错误，期望 dict，实际为 {type(angles).__name__}'
    assert 'left' in angles and 'right' in angles, f'返回结果缺少 left/right: {angles!r}'
    assert isinstance(angles['left'], (list, tuple)) and isinstance(angles['right'], (list, tuple))
    assert len(angles['left']) == 8 and len(angles['right']) == 8, f"左右臂数据长度应为 {8}，实际为 {len(angles['left'])}/{len(angles['right'])}"
    assert all((isinstance(value, (int, float)) for arm in angles.values() for value in arm))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
