# -*- coding: utf-8 -*-
import allure
import pytest
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase
from common1 import logger
cases = get_test_data_from_excel(TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE, 'get_upper_coords')

@allure.feature('UpperBody')
@allure.story('get_upper_coords')
@pytest.mark.upper_body
@pytest.mark.parametrize('case', cases, ids=lambda case: case['title'])
def test_get_upper_coords(upper_body, case):
    title = case['title']
    logger.info(f'》》》》》用例【{title}】开始测试《《《《《')
    with allure.step('调用 get_upper_coords 接口'):
        coords = upper_body.get_upper_coords()
        logger.debug('接口 get_upper_coords 返回：%r', coords)
    assert isinstance(coords, dict), f'返回类型错误，期望 dict，实际为 {type(coords).__name__}'
    assert 'left' in coords and 'right' in coords, f'返回结果缺少 left/right: {coords!r}'
    assert isinstance(coords['left'], (list, tuple)) and isinstance(coords['right'], (list, tuple))
    assert len(coords['left']) == 6 and len(coords['right']) == 6, f"左右臂数据长度应为 {6}，实际为 {len(coords['left'])}/{len(coords['right'])}"
    assert all((isinstance(value, (int, float)) for arm in coords.values() for value in arm))
    logger.info(f'✅ 用例【{title}】测试通过')
    logger.info(f'》》》》》用例【{title}】测试完成《《《《《')
