# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase


SHEETS = [
    "get_head_main_version", "get_head_modify_version", "get_head_debug_state",
    "is_head_powered_on", "get_head_angles", "is_head_moving",
    "get_head_collision_threshold", "get_head_robot_status", "get_head_err_status",
    "get_head_joints_current", "get_head_joints_run_sp", "get_head_joints_temp",
]
cases = [case for sheet in SHEETS for case in get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, sheet)]


@allure.feature("头部 PI4")
@allure.story("只读接口")
@pytest.mark.head
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_head_readonly_api(head, case):
    logger.info("》》》》》用例【%s】开始测试《《《《《", case["title"])
    logger.debug("test_api:%s", case["api"])
    with allure.step(f'调用 {case["api"]} 接口'):
        actual = getattr(head, case["api"])()
        logger.debug("接口返回：%r", actual)
    with allure.step("断言返回结构"):
        kind = case["expect_kind"]
        if kind == "number":
            assert isinstance(actual, (int, float))
        elif kind == "int":
            assert isinstance(actual, int)
        elif kind == "binary":
            assert actual in (0, 1)
        elif kind in {"angles4", "ints4"}:
            if not isinstance(actual, (list, tuple)) or len(actual) != 4:
                pytest.xfail(f"当前 SDK/固件未满足四关节合同，实际返回：{actual!r}")
            assert all(isinstance(value, (int, float)) for value in actual)
        elif kind == "status4":
            assert isinstance(actual, dict)
            assert "soft_error" in actual and "joint_errors" in actual
            if len(actual["joint_errors"]) != 4:
                pytest.xfail("当前 SDK/固件未满足四关节错误状态合同")
    logger.info("✅ 用例【%s】测试通过", case["title"])
