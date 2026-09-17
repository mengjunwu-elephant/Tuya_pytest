"""rclpy 服务客户端封装。"""

from __future__ import annotations

import threading
import time
from typing import Any, Type

from ..domain.policy import FailurePolicy
from ..errors import AgingError, CommunicationResponseError
from ..report.collector import ReportCollector
from ..report.log_setup import logger

try:
    import rclpy
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
except ImportError:  # pragma: no cover
    rclpy = None  # type: ignore


class RosBridge:
    """单节点 + 后台 spin；所有子系统共用。"""

    def __init__(
        self,
        report: ReportCollector,
        policy: FailurePolicy,
        *,
        service_timeout: float = 10.0,
    ) -> None:
        if rclpy is None:
            raise AgingError(
                "未安装 rclpy，请在机器人本机 source ROS2 后再运行"
            )
        if not rclpy.ok():
            rclpy.init()
        self.report = report
        self.policy = policy
        self.service_timeout = service_timeout
        self._lock = threading.RLock()
        self._clients: dict[str, Any] = {}
        self.node = rclpy.create_node("tuya_ros2_aging")
        self._callback_group = ReentrantCallbackGroup()
        self._executor = MultiThreadedExecutor()
        self._executor.add_node(self.node)
        self._spin_stop = threading.Event()
        self._spin_thread = threading.Thread(
            target=self._spin, name="RosSpin", daemon=True
        )
        self._spin_thread.start()

    def _spin(self) -> None:
        while not self._spin_stop.is_set() and rclpy.ok():
            try:
                self._executor.spin_once(timeout_sec=0.1)
            except Exception as exc:  # pragma: no cover
                logger.warning("ROS spin 异常: %s", exc)

    def close(self) -> None:
        self._spin_stop.set()
        self._spin_thread.join(timeout=2.0)
        try:
            self.node.destroy_node()
        except Exception:
            pass
        if rclpy is not None and rclpy.ok():
            try:
                rclpy.shutdown()
            except Exception:
                pass

    def _client(self, name: str, srv_type: Type[Any]) -> Any:
        with self._lock:
            client = self._clients.get(name)
            if client is None:
                client = self.node.create_client(
                    srv_type, name, callback_group=self._callback_group
                )
                self._clients[name] = client
            return client

    def call(
        self,
        subsystem: str,
        name: str,
        srv_type: Type[Any],
        request: Any,
        *,
        kind: str = "读取",
        timeout: float | None = None,
        require_success: bool = True,
    ) -> Any:
        """调用 Service；失败抛 CommunicationResponseError。

        require_success=False 时仍返回响应（用于上电查询等：
        success=false 表示业务态而非通信失败）。
        """
        wait_timeout = self.service_timeout if timeout is None else timeout
        started = time.monotonic()
        client = self._client(name, srv_type)
        api = name
        self.report.count(f"{subsystem}:{api}", "调用")
        logger.info(
            "ROS下发 | subsystem=%s | service=%s | request=%r",
            subsystem,
            name,
            _request_repr(request),
        )
        if not client.wait_for_service(timeout_sec=min(wait_timeout, 5.0)):
            msg = f"服务不可用: {name}"
            self.report.count(f"{subsystem}:{api}", "失败")
            if kind == "运动":
                self.policy.record_command_response(
                    subsystem, responded=False, api=api
                )
            raise CommunicationResponseError(msg, timeout=True)
        try:
            future = client.call_async(request)
            deadline = time.monotonic() + wait_timeout
            while not future.done():
                if time.monotonic() >= deadline:
                    msg = f"服务超时: {name}"
                    self.report.count(f"{subsystem}:{api}", "超时")
                    if kind == "运动":
                        self.policy.record_command_response(
                            subsystem, responded=False, api=api
                        )
                    raise CommunicationResponseError(msg, timeout=True)
                time.sleep(0.01)
            response = future.result()
        except CommunicationResponseError:
            raise
        except Exception as exc:
            self.report.count(f"{subsystem}:{api}", "失败")
            if kind == "运动":
                self.policy.record_command_response(
                    subsystem, responded=False, api=api
                )
            raise CommunicationResponseError(str(exc), timeout=False) from exc
        elapsed = time.monotonic() - started
        success = bool(getattr(response, "success", True))
        message = str(getattr(response, "message", "") or "")
        logger.info(
            "ROS反馈 | subsystem=%s | service=%s | elapsed=%.3fs"
            " | success=%s | message=%r",
            subsystem,
            name,
            elapsed,
            success,
            message,
        )
        if not success and require_success:
            self.report.count(f"{subsystem}:{api}", "失败")
            if kind == "运动":
                self.policy.record_command_response(
                    subsystem, responded=True, api=api
                )
            raise CommunicationResponseError(
                f"{name} 失败: {message or response!r}", timeout=False
            )
        self.report.count(
            f"{subsystem}:{api}", "成功" if success else "业务失败"
        )
        if kind == "运动":
            self.policy.record_command_response(
                subsystem, responded=True, api=api
            )
        return response


def _request_repr(request: Any) -> str:
    getter = getattr(request, "get_fields_and_field_types", None)
    if not callable(getter):
        return repr(request)
    fields = []
    for name in getter():
        try:
            fields.append(f"{name}={getattr(request, name)!r}")
        except Exception:
            continue
    if fields:
        return "{" + ", ".join(fields) + "}"
    return repr(request)
