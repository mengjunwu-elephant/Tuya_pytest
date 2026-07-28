# -*- coding: utf-8 -*-
import allure
import pytest

from common1.test_data_handler import get_test_data_from_excel
from settings import TuyaRobotBase


cases = get_test_data_from_excel(TuyaRobotBase.HEAD_TEST_DATA_FILE, "head_firmware_flash")


@allure.feature("头部 PI4")
@allure.story("固件升级参数校验")
@pytest.mark.head
@pytest.mark.firmware
@pytest.mark.parametrize("case", cases, ids=lambda c: c["title"])
def test_head_firmware_flash_invalid_file(head, case):
    before = head.get_head_main_version()
    result = head.head_firmware_flash(
        case["firmware_path"], case["main_version"], case["modified_version"], timeout=case["timeout"]
    )
    assert not result.ok
    assert head.get_head_main_version() == before
