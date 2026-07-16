# -*- coding: utf-8 -*-
"""跨接口复用的数学比较算法。

接口返回类型、字段结构、状态码和业务结果必须直接写在对应测试文件中，
避免把 SDK 接口契约隐藏到公共断言层。
"""
from __future__ import annotations

from numbers import Real

import allure


def assert_almost_equal(actual, expected, tol=5, name="值") -> None:
    """比较数值或等长数值序列，要求每项绝对偏差不超过 ``tol``。"""
    if isinstance(actual, Real) and isinstance(expected, Real):
        _assert_single_value(actual, expected, tol, name)
        return

    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected), (
            f"{name} 长度不一致：实际 {len(actual)}，期望 {len(expected)}"
        )
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            _assert_single_value(
                actual_item,
                expected_item,
                tol,
                f"{name}[{index}]",
            )
        return

    raise TypeError(
        f"不支持的数据类型：actual={type(actual)}, expected={type(expected)}"
    )


def _assert_single_value(actual, expected, tol, name) -> None:
    delta = abs(actual - expected)
    allure.attach(
        f"期望：{expected}\n实际：{actual}\n容差：±{tol}\n偏差：{delta}",
        name=name,
        attachment_type=allure.attachment_type.TEXT,
    )
    assert delta <= tol, (
        f"{name} 超出容差 ±{tol}：期望 {expected}，实际 {actual}，偏差 {delta}"
    )
