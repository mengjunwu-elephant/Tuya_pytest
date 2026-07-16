# -*- coding: utf-8 -*-
"""TuyaRobot pytest 图形启动器。"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from settings import TuyaConnectionConfig


ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "全部": "testcases/robot testcases/upper_body testcases/chassis",
    "整机": "testcases/robot",
    "上半身与头部": "testcases/upper_body",
    "底盘": "testcases/chassis",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TuyaRobot 自动化测试")
        self.resize(920, 650)
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)

        defaults = TuyaConnectionConfig.from_env()
        self.ip = QLineEdit(defaults.upper_ip)
        self.upper_port = QLineEdit(str(defaults.upper_port))
        self.head_port = QLineEdit(defaults.head_port)
        self.head_baud = QLineEdit(str(defaults.head_baud))
        self.chassis_port = QLineEdit(defaults.chassis_port)
        self.chassis_baud = QLineEdit(str(defaults.chassis_baud))
        self.module = QComboBox()
        self.module.addItems(MODULES)
        self.connect_head = QCheckBox("连接头部")
        self.run_motion = QCheckBox("允许运动测试")
        self.run_manual = QCheckBox("运行人工确认测试")
        self.run_danger = QCheckBox("运行高风险测试")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)

        form = QFormLayout()
        form.addRow("上半身 IP", self.ip)
        form.addRow("上半身端口", self.upper_port)
        form.addRow("头部串口", self.head_port)
        form.addRow("头部波特率", self.head_baud)
        form.addRow("底盘串口", self.chassis_port)
        form.addRow("底盘波特率", self.chassis_baud)
        form.addRow("测试域", self.module)

        checks = QHBoxLayout()
        checks.addWidget(self.connect_head)
        checks.addWidget(self.run_motion)
        checks.addWidget(self.run_manual)
        checks.addWidget(self.run_danger)
        checks.addStretch()

        self.collect_button = QPushButton("仅收集")
        self.run_button = QPushButton("运行测试")
        self.stop_button = QPushButton("停止")
        self.collect_button.clicked.connect(lambda: self._start(collect_only=True))
        self.run_button.clicked.connect(lambda: self._start(collect_only=False))
        self.stop_button.clicked.connect(self.process.kill)
        buttons = QHBoxLayout()
        buttons.addWidget(self.collect_button)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("TuyaRobot 连接配置"))
        layout.addLayout(form)
        layout.addLayout(checks)
        layout.addLayout(buttons)
        layout.addWidget(self.output, 1)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def _pytest_args(self, collect_only: bool) -> list[str]:
        paths = MODULES[self.module.currentText()].split()
        args = ["-m", "pytest", *paths, "--run-hardware"]
        if collect_only:
            args.append("--collect-only")
        else:
            args.append("--alluredir=allure-results")
        args.extend(
            [
                "--tuya-ip",
                self.ip.text().strip(),
                "--tuya-port",
                self.upper_port.text().strip(),
                "--head-port",
                self.head_port.text().strip(),
                "--head-baud",
                self.head_baud.text().strip(),
                "--chassis-port",
                self.chassis_port.text().strip(),
                "--chassis-baud",
                self.chassis_baud.text().strip(),
            ]
        )
        if self.connect_head.isChecked():
            args.append("--connect-head")
        if self.run_motion.isChecked():
            args.append("--run-motion")
        if self.run_manual.isChecked():
            args.append("--run-manual")
        if self.run_danger.isChecked():
            args.append("--run-danger")
        return args

    def _start(self, collect_only: bool) -> None:
        if self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, "提示", "已有测试进程正在运行")
            return
        self.output.clear()
        args = self._pytest_args(collect_only)
        self.output.appendPlainText(f"> {sys.executable} {' '.join(args)}\n")
        self.process.start(sys.executable, args)

    def _read_stdout(self) -> None:
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.output.insertPlainText(text)

    def _read_stderr(self) -> None:
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self.output.insertPlainText(text)

    def _finished(self, exit_code: int) -> None:
        self.output.appendPlainText(f"\n进程结束，退出码：{exit_code}")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())
