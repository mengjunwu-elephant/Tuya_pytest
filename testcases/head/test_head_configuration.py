# -*- coding: utf-8 -*-
import allure
import pytest

from common1 import logger
from common1.test_data_handler import get_test_data_from_excel
from common1.operator_input import prompt_continue
from settings import TuyaRobotBase


def _cases(sheet):
    return get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, sheet)


@allure.feature("头部 PI4")
@allure.story("可恢复配置")
@pytest.mark.head
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", _cases("set_head_debug_state"), ids=lambda c: c["title"])
def test_set_head_debug_state(head, case):
    original = head.get_head_debug_state()
    try:
        assert head.set_head_debug_state(case["state"]) == case["expect_data"]
        assert head.get_head_debug_state() == case["state"]
    finally:
        head.set_head_debug_state(original)
        assert head.get_head_debug_state() == original


@allure.feature("头部 PI4")
@allure.story("碰撞阈值")
@pytest.mark.head
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", _cases("set_head_collision_threshold"), ids=lambda c: c["title"])
def test_set_head_collision_threshold(head, case):
    original = head.get_head_collision_threshold()
    try:
        assert head.set_head_collision_threshold(case["threshold"]) == case["expect_data"]
        assert head.get_head_collision_threshold() == case["threshold"]
    finally:
        head.set_head_collision_threshold(original)
        assert head.get_head_collision_threshold() == original


@allure.feature("头部 PI4")
@allure.story("上电与下电")
@pytest.mark.head
@pytest.mark.danger
@pytest.mark.reset
@pytest.mark.parametrize("case", _cases("head_power_on") + _cases("head_power_off"), ids=lambda c: c["title"])
def test_head_power_switch(head, case):
    original = head.is_head_powered_on()
    method = getattr(head, case["api"])
    try:
        assert method() == case["expect_data"]
        assert head.is_head_powered_on() == (1 if case["api"] == "head_power_on" else 0)
    finally:
        (head.head_power_on if original else head.head_power_off)()


@allure.feature("头部 PI4")
@allure.story("使能与校准")
@pytest.mark.head
@pytest.mark.manual
@pytest.mark.danger
@pytest.mark.parametrize("case", _cases("set_head_joint_enable") + _cases("set_head_calibrate") + _cases("clear_head_error"), ids=lambda c: c["title"])
def test_head_manual_configuration(head, case):
    prompt_continue(f'请确认满足前置条件后执行：{case["title"]}')
    if case["api"] == "set_head_joint_enable":
        assert head.set_head_joint_enable(case["joint_id"], case["state"]) == case["expect_data"]
        restore = case["restore_value"]
        assert restore in (0, 1), "Excel 必须提供使能恢复状态"
        head.set_head_joint_enable(case["joint_id"], restore)
    elif case["api"] == "set_head_calibrate":
        assert head.set_head_calibrate(case["joint_id"]) == case["expect_data"]
        prompt_continue("请人工确认校准后的零位和错误状态。")
    else:
        assert head.clear_head_error(case["joint_id"]) == case["expect_data"]
