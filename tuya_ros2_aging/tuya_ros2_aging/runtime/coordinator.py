"""老化线程、停止策略、状态恢复和 ROS 生命周期协调器。"""

from __future__ import annotations

import signal
import threading
import time

from .. import constants
from ..config import AgingOptions
from ..device.chassis import ChassisDevice
from ..device.head import HeadDevice
from ..device.upper import UpperBodyDevice
from ..domain.context import AgingContext
from ..domain.policy import FailurePolicy
from ..monitor.chassis_monitor import ChassisMonitor
from ..monitor.head_monitor import HeadMonitor
from ..monitor.upper_monitor import UpperMonitor
from ..motion.chassis_runner import ChassisMotionRunner
from ..motion.head_runner import HeadMotionRunner
from ..motion.upper_runner import UpperMotionRunner
from ..report.collector import ReportCollector
from ..report.log_setup import logger
from ..ros.client import RosBridge


class AgingCoordinator:
    def __init__(
        self,
        options: AgingOptions,
        report: ReportCollector,
    ) -> None:
        self.options = options
        self.report = report
        self.stop_event = threading.Event()
        self.upper_blocking_motion = threading.Event()
        self.head_blocking_motion = threading.Event()
        self.head_stop_event = threading.Event()
        self.head_ready = threading.Event()
        self.fatal_lock = threading.Lock()
        self.head_stop_lock = threading.Lock()
        self.finished_lock = threading.Lock()
        self.fatal_reason = ""
        self.head_stop_reason = ""
        self.shutdown_reason = ""
        self.finished_motion: set[str] = set()
        self.policy = FailurePolicy(
            options.consecutive_motion_failure_limit, report
        )
        self.bridge = RosBridge(
            report,
            self.policy,
            service_timeout=options.service_timeout,
        )
        self.upper_device = UpperBodyDevice(self.bridge)
        self.chassis_device = ChassisDevice(self.bridge)
        self.head_device = HeadDevice(self.bridge)
        self.context = AgingContext(
            options=options,
            report=report,
            policy=self.policy,
            stop_event=self.stop_event,
            fatal=self.fatal,
            stop_head_motion=self.stop_head_motion,
            upper_blocking_motion=self.upper_blocking_motion,
            head_blocking_motion=self.head_blocking_motion,
            head_stop_event=self.head_stop_event,
            head_ready=self.head_ready,
        )
        self.upper_runner = UpperMotionRunner(
            self.upper_device, self.context
        )
        self.chassis_runner = ChassisMotionRunner(
            self.chassis_device, self.context
        )
        self.head_runner = HeadMotionRunner(
            self.head_device, self.context
        )
        self.upper_monitor = UpperMonitor(
            self.upper_device, self.context
        )
        self.chassis_monitor = ChassisMonitor(
            self.chassis_device, self.context
        )
        self.head_monitor = HeadMonitor(
            self.head_device, self.context
        )

    def fatal(
        self, subsystem: str, phase: str, exc: BaseException | str
    ) -> None:
        with self.fatal_lock:
            if self.fatal_reason:
                return
            if isinstance(exc, BaseException):
                message = str(exc)
                exception = exc
            else:
                message = exc
                exception = None
            self.fatal_reason = f"{subsystem}/{phase}: {message}"
            self.shutdown_reason = "fatal"
            logger.error("触发全局停止：%s", self.fatal_reason)
            self.report.event(
                "FATAL", subsystem, phase, message, exception
            )
            self.stop_event.set()
            self.head_stop_event.set()

    def stop_head_motion(
        self, phase: str, exc: BaseException | str
    ) -> None:
        with self.head_stop_lock:
            if self.head_stop_reason:
                return
            if isinstance(exc, BaseException):
                message = str(exc)
                exception = exc
            else:
                message = exc
                exception = None
            self.head_stop_reason = f"头部/{phase}: {message}"
            logger.error(
                "触发头部局部停止（上半身/底盘继续）：%s",
                self.head_stop_reason,
            )
            self.report.event(
                "ERROR", "头部", phase, message, exception
            )
            self.head_stop_event.set()

    def _mark_finished(self, name: str) -> None:
        with self.finished_lock:
            self.finished_motion.add(name)

    def _run_upper_motion(self) -> None:
        try:
            self.upper_runner.run()
        finally:
            self._mark_finished("upper")

    def _run_chassis_motion(self) -> None:
        try:
            self.chassis_runner.run()
        finally:
            self._mark_finished("chassis")

    def _run_head_motion(self) -> None:
        try:
            self.head_runner.run()
        finally:
            self._mark_finished("head")

    def _report_worker(self) -> None:
        while not self.stop_event.wait(self.options.autosave_interval):
            try:
                self.report.save()
            except Exception as exc:
                self.fatal("报告", "定时保存", exc)
                return

    def _requested_motion_finished(self) -> bool:
        expected = set()
        if self.options.run_upper_motion:
            expected.add("upper")
        if self.options.run_chassis_motion:
            expected.add("chassis")
        if self.options.run_head_motion:
            expected.add("head")
        if not expected:
            return False
        with self.finished_lock:
            return expected <= self.finished_motion

    def _build_threads(self) -> list[threading.Thread]:
        threads = [
            threading.Thread(
                target=self._report_worker,
                name="ReportSaver",
                daemon=True,
            )
        ]
        if self.options.run_upper_motion or self.options.monitor_only:
            threads.append(
                threading.Thread(
                    target=self.upper_monitor.run,
                    name="UpperMonitor",
                    daemon=True,
                )
            )
        if self.options.run_chassis_motion or self.options.monitor_only:
            threads.append(
                threading.Thread(
                    target=self.chassis_monitor.run,
                    name="ChassisMonitor",
                    daemon=True,
                )
            )
        if self.options.run_head_motion or self.options.monitor_only:
            threads.append(
                threading.Thread(
                    target=self.head_monitor.run,
                    name="HeadMonitor",
                    daemon=True,
                )
            )
        if self.options.run_upper_motion:
            threads.append(
                threading.Thread(
                    target=self._run_upper_motion,
                    name="UpperMotion",
                    daemon=True,
                )
            )
        if self.options.run_chassis_motion:
            threads.append(
                threading.Thread(
                    target=self._run_chassis_motion,
                    name="ChassisMotion",
                    daemon=True,
                )
            )
        if self.options.run_head_motion:
            threads.append(
                threading.Thread(
                    target=self._run_head_motion,
                    name="HeadMotion",
                    daemon=True,
                )
            )
        return threads

    def _emergency_stop(self) -> None:
        if self.options.run_chassis_motion:
            try:
                self.chassis_device.stop()
            except Exception as exc:
                self.report.event(
                    "ERROR", "底盘", "全局清理", "停止底盘失败", exc
                )
        if self.options.run_upper_motion:
            try:
                self.upper_device.upper_stop()
            except Exception as exc:
                self.report.event(
                    "ERROR", "上半身", "全局清理", "上半身急停失败", exc
                )
        if self.options.run_head_motion:
            self.head_stop_event.set()
            try:
                self.head_device.stop()
            except Exception as exc:
                self.report.event(
                    "ERROR", "头部", "全局清理", "头部停止失败", exc
                )

    def _restore(self) -> None:
        if not self.fatal_reason and self.options.run_upper_motion:
            try:
                self.upper_device.go_zero(
                    threading.Event(),
                    self.options.upper_timeout,
                    force=True,
                )
            except Exception as exc:
                self.report.event(
                    "ERROR", "上半身", "正常退出回零", "回零失败", exc
                )
            try:
                self.upper_device.ensure_fresh_mode()
            except Exception as exc:
                self.report.event(
                    "ERROR", "上半身", "恢复刷新模式", str(exc), exc
                )
        if not self.fatal_reason and self.options.run_head_motion:
            try:
                self.head_device.go_zero(
                    threading.Event(),
                    self.options.head_timeout,
                    force=True,
                    speed=self.options.head_speed,
                )
            except Exception as exc:
                self.report.event(
                    "ERROR", "头部", "正常退出回零", "回零失败", exc
                )
            try:
                self.head_device.set_led(*constants.HEAD_LED_RESTORE)
            except Exception as exc:
                self.report.event(
                    "ERROR", "头部", "恢复LED", "恢复 LED 失败", exc
                )

    def run(self) -> int:
        def _on_signal(signum: int, _frame: object) -> None:
            logger.warning("收到信号 %s，准备停止", signum)
            self.shutdown_reason = "signal"
            self.stop_event.set()
            self.head_stop_event.set()

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
        threads = self._build_threads()
        for thread in threads:
            thread.start()
        deadline = None
        if self.options.duration_hours > 0:
            deadline = (
                time.monotonic() + self.options.duration_hours * 3600.0
            )
        try:
            while not self.stop_event.is_set():
                if deadline is not None and time.monotonic() >= deadline:
                    logger.info("达到设定运行时长，准备停止")
                    self.shutdown_reason = "duration"
                    self.stop_event.set()
                    self.head_stop_event.set()
                    break
                if self._requested_motion_finished():
                    logger.info("设定的运动循环已全部完成")
                    self.shutdown_reason = "cycle_limit"
                    self.stop_event.set()
                    self.head_stop_event.set()
                    break
                time.sleep(0.2)
        finally:
            self.stop_event.set()
            self.head_stop_event.set()
            self._emergency_stop()
            for thread in threads:
                thread.join(timeout=30.0)
            self._restore()
            self.report.save()
            self.bridge.close()
            logger.info(
                "老化结束 | reason=%s | fatal=%s | head_stop=%s",
                self.shutdown_reason or "unknown",
                self.fatal_reason or "-",
                self.head_stop_reason or "-",
            )
        return 1 if self.fatal_reason else 0
