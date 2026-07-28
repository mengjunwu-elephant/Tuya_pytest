# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase

cases = get_test_data_from_excel(
    TuyaRobotBase.UPPER_BODY_TEST_DATA_FILE,
    "upper_run_dynamic_identify_traj",
)


@allure.feature("上半身动力学辨识")
@allure.story("SDK暂不支持动力学辨识轨迹")
@pytest.mark.upper_body
@pytest.mark.manual
@pytest.mark.motion
@pytest.mark.danger
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_upper_run_dynamic_identify_traj(upper_body, case):
    title = case["title"]
    logger.info(f"》》》》》用例【{title}】开始测试《《《《《")
    logger.debug(f'test_api:{case["api"]}')
    pytest.skip("当前安装的 pytuyarobot SDK 未提供 upper_run_dynamic_identify_traj 接口")
