"""老化脚本异常类型。"""

from __future__ import annotations

import json
from typing import Any


class AgingError(RuntimeError):
    """老化流程业务异常。"""


class CommunicationResponseError(AgingError):
    def __init__(self, status_code: Any, message: Any, blocked_by: Any) -> None:
        self.status_code = status_code
        self.message = str(message or "")
        self.blocked_by = blocked_by
        details = {
            "status_code": status_code,
            "message": message,
            "blocked_by": blocked_by,
        }
        super().__init__(
            "TuyaRobot 命令执行失败: "
            f"{json.dumps(details, ensure_ascii=False, default=str)}"
        )

    @property
    def is_timeout(self) -> bool:
        return "timeout" in self.message.lower()


class EmptyResponseError(AgingError):
    """查询或运动接口未返回可用数据。"""


class ConsecutiveMotionFailureError(AgingError):
    """连续运动无响应或未成功达到停止阈值。"""


class SafetyViolationError(AgingError):
    """软件限位越界或设备明确错误状态。"""
