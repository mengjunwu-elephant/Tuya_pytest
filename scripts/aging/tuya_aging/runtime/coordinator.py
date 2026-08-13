"""老化线程、停止策略、状态恢复和连接生命周期协调器。"""

from __future__ import annotations

import signal
import threading
import time
from typing import Any

from .. import constants
from ..config import AgingConnectionConfig, AgingOptions
from ..device import (
    ChassisDevice,
    HeadDevice,
    TuyaConnection,
    TuyaGateway,
    UpperBodyDevice,
)
from ..domain.policy import FailurePolicy
from ..domain.context import AgingContext
from ..monitor import ChassisMonitor, HeadMonitor, UpperMonitor
from ..motion import (
    ChassisMotionRunner,
    HeadMotionRunner,
    UpperMotionRunner,
)
from ..report.collector import ReportCollector
from ..report.log_setup import logger


class AgingCoordinator:
    def __init__(
        self,
        connection_config: AgingConnectionConfig,
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
        self.connection = TuyaConnection(
            connection_config,
            connect_chassis=(
                options.run_chassis_motion or options.monitor_only
            ),
            connect_head=(
                options.run_head_motion or options.monitor_only
            ),
        )
        self.policy = FailurePolicy(
            options.consecutive_motion_failure_limit, report
        )
        self.gateway = TuyaGateway(report, self.policy)
        self.upper_device = UpperBodyDevice(
            self.connection.robot, self.gateway
        )
        self.chassis_device = ChassisDevice(
            self.connection.robot, self.gateway
        )
        self.head_device = HeadDevice(
            self.connection.robot, self.gateway
        )
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
        # 头部运动先于监控启动，保证上电确认期间独占链路
        if self.options.run_head_motion:
            threads.append(
                threading.Thread(
                    target=self._run_head_motion,
                    name="HeadMotion",
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
                )
            )
        if self.options.run_chassis_motion:
            threads.append(
                threading.Thread(
                    target=self._run_chassis_motion,
                    name="ChassisMotion",
                )
            )
        return threads

    def _safe_stop(self) -> None:
        if self.shutdown_reason not in {"fatal", "interrupt", "duration"}:
            return
        if self.options.run_chassis_motion:
            try:
                self.chassis_device.stop()
            except Exception as exc:
                self.report.event(
                    "ERROR", "底盘", "全局清理", "停止底盘失败", exc
                )
        if self.options.run_upper_motion:
            try:
                self.upper_device.call(
                    self.upper_device.upper_body.upper_stop
                )
            except Exception as exc:
                self.report.event(
                    "ERROR", "上半身", "全局清理", "上半身急停失败", exc
                )
        if self.options.run_head_motion:
            # 头部无独立急停接口：靠局部/全局停止事件打断等待并回零
            self.head_stop_event.set()

    def _restore(self) -> None:
        if (
            not self.fatal_reason
            and self.options.run_upper_motion
        ):
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
        if (
            not self.fatal_reason
            and self.options.run_head_motion
        ):
            try:
                self.head_device.go_zero(
                    threading.Event(),
                    self.options.head_timeout,
                    force=True,
                    speed=self.options.head_speed,
                    tolerance=constants.HEAD_ANGLE_TOLERANCE,
                )
            except Exception as exc:
                self.report.event(
                    "ERROR", "头部", "正常退出回零", "回零失败", exc
                )
            try:
                self.head_device.call(
                    self.head_device.head.set_head_led_control,
                    *constants.HEAD_LED_RESTORE,
                )
            except Exception as exc:
                self.report.event(
                    "ERROR", "头部", "恢复LED", "恢复 LED 失败", exc
                )
        modes = self.upper_runner.original_fresh_modes
        if (
            self.options.run_upper_motion
            and isinstance(modes, (list, tuple))
            and len(modes) == 2
        ):
            try:
                self.upper_device.call(
                    self.upper_device.left_arm.set_upper_fresh_mode,
                    int(modes[0]),
                )
                self.upper_device.call(
                    self.upper_device.right_arm.set_upper_fresh_mode,
                    int(modes[1]),
                )
            except Exception as exc:
                self.report.event(
                    "ERROR", "上半身", "恢复模式",
                    "恢复刷新模式失败", exc,
                )
        original_auto = self.chassis_monitor.original_auto_report
        if original_auto is not None:
            try:
                current = int(
                    self.chassis_device.call(
                        self.chassis_device.chassis.get_agv_auto_report
                    )
                )
                if current != original_auto:
                    self.chassis_device.call(
                        self.chassis_device.chassis.set_agv_auto_report,
                        original_auto,
                    )
            except Exception as exc:
                self.report.event(
                    "ERROR", "底盘", "恢复自动上报",
                    "恢复自动上报状态失败", exc,
                )

    def _record_overlap(self) -> None:
        upper_start = self.upper_runner.active_start
        upper_end = self.upper_runner.active_end
        chassis_start = self.chassis_runner.active_start
        chassis_end = self.chassis_runner.active_end
        if None not in (
            upper_start, upper_end, chassis_start, chassis_end
        ):
            overlap = max(
                0.0,
                min(float(upper_end), float(chassis_end))
                - max(float(upper_start), float(chassis_start)),
            )
            self.report.count(
                "运行", "上半身底盘运动重叠秒", overlap
            )
        self.report.count(
            "运行",
            "上半身底盘同时启用",
            1.0
            if self.options.run_upper_motion
            and self.options.run_chassis_motion
            else 0.0,
        )
        self.report.count(
            "运行",
            "头部运动启用",
            1.0 if self.options.run_head_motion else 0.0,
        )
        if self.head_stop_reason:
            self.report.count("运行", "头部局部停止", 1.0)

    def _install_signal_handlers(self) -> None:
        def handle_signal(signum: int, _frame: Any) -> None:
            logger.info("收到系统信号 %s，准备停止", signum)
            self.shutdown_reason = "interrupt"
            self.stop_event.set()
            self.head_stop_event.set()

        for name in ("SIGINT", "SIGTERM"):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), handle_signal)

    def run(self) -> int:
        self._install_signal_handlers()
        threads = self._build_threads()
        started = time.monotonic()
        for thread in threads:
            thread.start()
        try:
            while not self.stop_event.wait(0.5):
                if (
                    self.options.duration_hours > 0
                    and time.monotonic() - started
                    >= self.options.duration_hours * 3600
                ):
                    self.shutdown_reason = "duration"
                    logger.info("达到设定运行时长，准备结束")
                    self.stop_event.set()
                    self.head_stop_event.set()
                    break
                if self._requested_motion_finished():
                    self.shutdown_reason = "completed"
                    logger.info("设定的运动循环已全部完成")
                    self.stop_event.set()
                    break
        except KeyboardInterrupt:
            self.shutdown_reason = "interrupt"
            logger.info("收到键盘中断，准备安全退出")
            self.stop_event.set()
            self.head_stop_event.set()
        finally:
            try:
                self._safe_stop()
                for thread in threads:
                    thread.join(timeout=10)
                self._restore()
                self._record_overlap()
                self.report.save()
            finally:
                self.connection.close()
        return 1 if self.fatal_reason else 0
