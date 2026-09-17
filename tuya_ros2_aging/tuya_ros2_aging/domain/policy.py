"""统一的运动失败与停止策略。"""

from __future__ import annotations

import threading
from typing import Protocol

from ..errors import ConsecutiveMotionFailureError
from .models import MotionOutcome


class CounterSink(Protocol):
    def count(
        self, category: str, metric: str, amount: float = 1.0
    ) -> None: ...

    def set_max(self, category: str, metric: str, value: float) -> None: ...


class FailurePolicy:
    def __init__(self, limit: int, stats: CounterSink) -> None:
        self.limit = limit
        self.stats = stats
        self.lock = threading.Lock()
        self.action_streak = {"upper": 0, "chassis": 0, "head": 0}
        self.response_streak = {"upper": 0, "chassis": 0, "head": 0}

    @staticmethod
    def _prefix(subsystem: str) -> str:
        if subsystem == "upper":
            return "上半身"
        if subsystem == "head":
            return "头部"
        return "底盘"

    def record_command_response(
        self, subsystem: str, *, responded: bool, api: str
    ) -> None:
        prefix = self._prefix(subsystem)
        with self.lock:
            if responded:
                self.response_streak[subsystem] = 0
                return
            streak = self.response_streak[subsystem] + 1
            self.response_streak[subsystem] = streak
        category = f"{prefix}运动汇总"
        self.stats.count(category, "运动指令无响应")
        self.stats.set_max(
            category, "连续运动指令无响应最大次数", float(streak)
        )
        if streak >= self.limit:
            raise ConsecutiveMotionFailureError(
                f"{prefix}连续 {streak} 次运动指令无响应，"
                f"达到停止阈值 {self.limit}，最后接口 {api}"
            )

    def record_motion(
        self, subsystem: str, outcome: MotionOutcome
    ) -> None:
        prefix = self._prefix(subsystem)
        category = f"{prefix}运动汇总"
        self.stats.count(category, "调用")
        if outcome.reached and not outcome.exceeded:
            self.stats.count(category, "成功")
            self.stats.count(category, "达到目标点位次数")
            with self.lock:
                self.action_streak[subsystem] = 0
            return
        self.stats.count(category, "失败")
        self.stats.count(category, "未达到目标点位次数")
        if outcome.exceeded:
            self.stats.count(category, "越界")
        with self.lock:
            streak = self.action_streak[subsystem] + 1
            self.action_streak[subsystem] = streak
        self.stats.set_max(category, "连续运动失败最大次数", float(streak))
        if streak >= self.limit:
            raise ConsecutiveMotionFailureError(
                f"{prefix}连续 {streak} 个运动动作未成功，"
                f"达到停止阈值 {self.limit}"
            )
