"""跨层使用的纯函数。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def utc_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def excel_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def numeric_values(value: Any) -> list[float]:
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        result: list[float] = []
        for item in value.values():
            result.extend(numeric_values(item))
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(numeric_values(item))
        return result
    return []


def upper_status_has_error(status: Any) -> bool:
    if not isinstance(status, dict):
        return False
    return any(
        status.get(key, 0) not in (0, None)
        for key in ("status", "left_arm_error", "right_arm_error")
    )


def chassis_status_has_error(status: Any) -> bool:
    if not isinstance(status, dict):
        return False
    return any(
        status.get(key, 0) not in (0, None)
        for key in ("status", "left_motor_error", "right_motor_error")
    )


def head_status_has_error(status: Any) -> bool:
    if not isinstance(status, dict):
        return False
    soft_error = status.get("soft_error", 0)
    if soft_error not in (0, None, False):
        return True
    motor_errors = status.get("motor_errors")
    if isinstance(motor_errors, (list, tuple)):
        return any(value not in (0, None) for value in motor_errors)
    joint_errors = status.get("joint_errors")
    if isinstance(joint_errors, (list, tuple)):
        return any(value not in (0, None) for value in joint_errors)
    return False
