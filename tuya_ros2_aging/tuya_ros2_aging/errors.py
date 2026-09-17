"""老化异常类型。"""

from __future__ import annotations


class AgingError(RuntimeError):
    """老化流程业务异常。"""


class CommunicationResponseError(AgingError):
    def __init__(self, message: str, *, timeout: bool = False) -> None:
        self.message = message
        self.is_timeout = timeout
        super().__init__(message)


class EmptyResponseError(AgingError):
    """查询或运动接口未返回可用数据。"""


class ConsecutiveMotionFailureError(AgingError):
    """连续运动无响应或未成功达到停止阈值。"""


class SafetyViolationError(AgingError):
    """软件限位越界或设备明确错误状态。"""
