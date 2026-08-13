"""SDK 接口的唯一调用入口。"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

from pytuyarobot.command_result import CommandResult

from ..domain.models import CallOutcome
from ..domain.policy import FailurePolicy
from ..errors import CommunicationResponseError, EmptyResponseError
from ..report.collector import ReportCollector
from ..report.log_setup import logger


class TuyaGateway:
    _QUIET_SUCCESS_APIS = frozenset(
        {"get_upper_is_moving", "is_head_moving"}
    )

    def __init__(
        self,
        report: ReportCollector,
        policy: FailurePolicy,
    ) -> None:
        self.report = report
        self.policy = policy
        self.upper_lock = threading.RLock()
        self.chassis_lock = threading.RLock()
        self.head_lock = threading.RLock()

    @staticmethod
    def result_data(result: Any) -> Any:
        if isinstance(result, CommandResult):
            if not result.ok:
                raise CommunicationResponseError(
                    result.status_code,
                    result.message,
                    result.blocked_by,
                )
            return result.data
        return result

    @staticmethod
    def _api_name(func: Callable[..., Any]) -> str:
        return getattr(
            func, "__qualname__", getattr(func, "__name__", repr(func))
        )

    @staticmethod
    def _kind(api_name: str) -> str:
        name = api_name.rsplit(".", 1)[-1]
        if name.startswith(("get_", "is_")):
            return "读取"
        if (
            name == "upper_go_zero"
            or name == "agv_wheel_control"
            or name.startswith(
                (
                    "send_upper_",
                    "write_upper_",
                    "upper_jog_",
                    "send_head_",
                    "play_screen_",
                )
            )
        ):
            return "运动"
        return "控制"

    @classmethod
    def _log_success_calls(cls, api_name: str) -> bool:
        return api_name.rsplit(".", 1)[-1] not in cls._QUIET_SUCCESS_APIS

    @staticmethod
    def _empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (str, bytes, bytearray, list, tuple, dict, set)):
            return len(value) == 0
        return False

    @staticmethod
    def _timeout(exc: BaseException) -> bool:
        return isinstance(exc, TimeoutError) or (
            isinstance(exc, CommunicationResponseError) and exc.is_timeout
        )

    @staticmethod
    def _prefix(subsystem: str) -> str:
        if subsystem == "upper":
            return "上半身"
        if subsystem == "head":
            return "头部"
        return "底盘"

    def _metric(
        self, subsystem: str, api: str, metric: str
    ) -> None:
        prefix = self._prefix(subsystem)
        self.report.count(f"{prefix}通信汇总", metric)
        self.report.count(f"{prefix}通信/{api}", metric)

    def _call(
        self,
        subsystem: str,
        lock: threading.RLock,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        keep_raw: bool = False,
        use_lock: bool = True,
    ) -> Any:
        api = self._api_name(func)
        kind = self._kind(api)
        started = time.monotonic()
        context = lock if use_lock else _NullLock()
        with context:
            self._metric(subsystem, api, "调用")
            prefix = self._prefix(subsystem)
            log_success_calls = self._log_success_calls(api)
            if log_success_calls:
                logger.info(
                    "%s接口下发 | api=%s | args=%r | kwargs=%r",
                    prefix,
                    api,
                    args,
                    kwargs,
                )
            try:
                raw = func(*args, **kwargs)
                data = raw if keep_raw else self.result_data(raw)
                if kind in ("读取", "运动") and self._empty(data):
                    raise EmptyResponseError(
                        f"{prefix}{kind}接口 {api} 返回空数据: {data!r}"
                    )
            except Exception as exc:
                timeout = self._timeout(exc)
                empty = isinstance(exc, EmptyResponseError)
                self._metric(subsystem, api, "失败")
                if timeout:
                    self._metric(subsystem, api, "超时")
                elif empty:
                    self._metric(subsystem, api, "空返回")
                if kind == "运动":
                    self.policy.record_command_response(
                        subsystem,
                        responded=not (timeout or empty),
                        api=api,
                    )
                logger.warning(
                    "%s接口失败，已记录统计 | api=%s | error=%s",
                    prefix,
                    api,
                    exc,
                    exc_info=True,
                )
                raise
            self._metric(subsystem, api, "成功")
            if kind == "运动":
                self.policy.record_command_response(
                    subsystem, responded=True, api=api
                )
        outcome = CallOutcome(
            api=api,
            subsystem=subsystem,
            kind=kind,
            responded=True,
            succeeded=True,
            data=data,
            raw=raw,
            elapsed=time.monotonic() - started,
        )
        if log_success_calls:
            logger.info(
                "%s接口反馈 | api=%s | raw=%r | data=%r | elapsed=%.3fs",
                prefix,
                api,
                raw,
                data,
                outcome.elapsed,
            )
        return data

    def upper(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return self._call(
            "upper", self.upper_lock, func, args, kwargs
        )

    def chassis(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return self._call(
            "chassis", self.chassis_lock, func, args, kwargs
        )

    def head(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return self._call(
            "head", self.head_lock, func, args, kwargs
        )

    def upper_blocking_raw(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return self._call(
            "upper",
            self.upper_lock,
            func,
            args,
            kwargs,
            keep_raw=True,
            use_lock=False,
        )


class _NullLock:
    def __enter__(self) -> "_NullLock":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None
