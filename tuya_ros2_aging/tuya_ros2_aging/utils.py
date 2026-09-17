"""跨层纯函数。"""

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


def poses_to_list(poses: Any) -> list[float]:
    """将 GetCartesianPoses 返回规范为平面 float 列表。"""
    if poses is None:
        return []
    if isinstance(poses, (list, tuple)):
        if not poses:
            return []
        first = poses[0]
        if isinstance(first, (int, float)):
            return [float(v) for v in poses]
        out: list[float] = []
        for pose in poses:
            if hasattr(pose, "x"):
                out.extend(
                    [
                        float(pose.x),
                        float(pose.y),
                        float(pose.z),
                        float(getattr(pose, "rx", 0.0)),
                        float(getattr(pose, "ry", 0.0)),
                        float(getattr(pose, "rz", 0.0)),
                    ]
                )
            elif isinstance(pose, (list, tuple)):
                out.extend(float(v) for v in pose)
            else:
                out.append(float(pose))
        return out
    return []


def scoped_angles(values: list[float]) -> dict[str, list[float]]:
    if len(values) == 8:
        return {"left": list(values)}
    if len(values) == 16:
        return {"left": list(values[:8]), "right": list(values[8:])}
    raise ValueError(f"角度长度错误: {len(values)}")


def scoped_coords(values: list[float]) -> dict[str, list[float]]:
    if len(values) == 6:
        return {"left": list(values)}
    if len(values) == 12:
        return {"left": list(values[:6]), "right": list(values[6:])}
    raise ValueError(f"坐标长度错误: {len(values)}")
