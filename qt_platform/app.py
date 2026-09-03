# -*- coding: utf-8 -*-
"""TuyaRobot pytest 图形启动器：三域勾选、门控校验、Allure 报告。"""
from __future__ import annotations

import codecs
import locale
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from settings import TuyaConnectionConfig

from qt_platform.gate_check import (
    GateState,
    SelectionSummary,
    format_run_confirm,
    validate_gates,
)
from qt_platform.runner import (
    ConnectionParams,
    build_allure_serve_args,
    build_probe_args,
    build_pytest_args,
    build_pytest_targets,
    format_command,
    new_allure_dir,
    python_executable,
)
from qt_platform.test_discovery import (
    DOMAIN_LABELS,
    DOMAIN_ORDER,
    DomainModuleRow,
    DiscoverResult,
    discover_by_domain,
)

ROOT = Path(__file__).resolve().parents[1]

# QTreeWidgetItem 自定义角色
_ROLE_KIND = Qt.ItemDataRole.UserRole  # "file" | "func"
_ROLE_DOMAIN = Qt.ItemDataRole.UserRole + 1
_ROLE_PATH = Qt.ItemDataRole.UserRole + 2
_ROLE_FUNC = Qt.ItemDataRole.UserRole + 3
_ROLE_ROW = Qt.ItemDataRole.UserRole + 4  # DomainModuleRow，仅文件节点
_ROLE_SEARCH = Qt.ItemDataRole.UserRole + 5  # 搜索用文本


def _utf8_child_environment() -> QProcessEnvironment:
    """让子进程用 UTF-8 输出，避免 Windows 本地代码页导致中文乱码。"""
    env = QProcessEnvironment.systemEnvironment()
    env.insert("PYTHONUTF8", "1")
    env.insert("PYTHONIOENCODING", "utf-8")
    return env


def _make_incremental_decoder(encoding: str, errors: str):
    try:
        return codecs.getincrementaldecoder(encoding)(errors=errors)
    except LookupError:
        return codecs.getincrementaldecoder("utf-8")(errors=errors)


class StreamDecoder:
    """增量解码进程输出：优先 UTF-8，遇到非法字节则整条流回退到系统本地编码。

    使用增量解码器是为了让跨读取块被截断的多字节字符继续拼接，
    否则截断会被误判成乱码。
    """

    def __init__(self) -> None:
        self._utf8 = _make_incremental_decoder("utf-8", "strict")
        self._fallback = None

    def feed(self, data: bytes) -> str:
        if self._fallback is None:
            try:
                return self._utf8.decode(data)
            except UnicodeDecodeError:
                encoding = locale.getpreferredencoding(False) or "utf-8"
                self._fallback = _make_incremental_decoder(encoding, "replace")
        return self._fallback.decode(data)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TuyaRobot 自动化测试")
        self.resize(1200, 780)

        self._discover: DiscoverResult | None = None
        self._domain_rows: dict[str, list[DomainModuleRow]] = {d: [] for d in DOMAIN_ORDER}
        self._trees: dict[str, QTreeWidget] = {}
        self._updating_tree = False
        self._last_allure_dir: Path | None = None
        self._pending_allure_dir: Path | None = None
        self._run_mode: str | None = None  # "pytest" | "probe" | "allure"
        self._stdout_decoder = StreamDecoder()
        self._stderr_decoder = StreamDecoder()

        child_env = _utf8_child_environment()
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProcessEnvironment(child_env)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)

        self.allure_process = QProcess(self)
        self.allure_process.setWorkingDirectory(str(ROOT))
        self.allure_process.setProcessEnvironment(child_env)

        defaults = TuyaConnectionConfig.from_env()
        self.ip = QLineEdit(defaults.upper_ip)
        self.upper_port = QLineEdit(str(defaults.upper_port))
        self.head_ip = QLineEdit(defaults.head_ip)
        self.head_port = QLineEdit(str(defaults.head_port))
        self.chassis_port = QLineEdit(defaults.chassis_port)
        self.chassis_baud = QLineEdit(str(defaults.chassis_baud))
        self.connect_head = QCheckBox("连接头部")
        self.connect_chassis = QCheckBox("连接底盘")
        self.connect_chassis.setChecked(True)
        self.run_motion = QCheckBox("允许运动测试")
        self.run_manual = QCheckBox("运行人工确认测试")
        self.run_danger = QCheckBox("运行高风险测试")
        self.run_firmware = QCheckBox("运行固件测试")

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索接口名 / 函数名 / story…")
        self.search.textChanged.connect(self._apply_search)

        self.summary_label = QLabel("已选：0 文件 / 0 函数（跨 0 域）")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)

        self.collect_button = QPushButton("仅收集")
        self.run_button = QPushButton("运行测试")
        self.stop_button = QPushButton("停止")
        self.report_button = QPushButton("打开报告")
        self.probe_button = QPushButton("连接探测")
        self.report_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.collect_button.clicked.connect(lambda: self._start_pytest(collect_only=True))
        self.run_button.clicked.connect(lambda: self._start_pytest(collect_only=False))
        self.stop_button.clicked.connect(self._stop_process)
        self.report_button.clicked.connect(self._open_report)
        self.probe_button.clicked.connect(self._start_probe)

        self._build_layout()
        self._load_cases()

    def _build_layout(self) -> None:
        # —— 左侧用例区 ——
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        for domain in DOMAIN_ORDER:
            tree = QTreeWidget()
            tree.setHeaderHidden(True)
            tree.setUniformRowHeights(True)
            tree.itemChanged.connect(self._on_item_changed)
            self._trees[domain] = tree
            self.tabs.addTab(tree, DOMAIN_LABELS[domain])
        left_layout.addWidget(self.tabs)
        left_layout.addWidget(self.search)

        tree_btns = QHBoxLayout()
        btn_select = QPushButton("全选当前域")
        btn_clear_domain = QPushButton("清空当前域")
        btn_clear_all = QPushButton("清空全部")
        btn_select.clicked.connect(self._select_current_domain)
        btn_clear_domain.clicked.connect(self._clear_current_domain)
        btn_clear_all.clicked.connect(self._clear_all)
        tree_btns.addWidget(btn_select)
        tree_btns.addWidget(btn_clear_domain)
        tree_btns.addWidget(btn_clear_all)
        left_layout.addLayout(tree_btns)

        # —— 右侧配置区 ——
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        conn_box = QGroupBox("连接配置")
        form = QFormLayout(conn_box)
        form.addRow("上半身 IP", self.ip)
        form.addRow("上半身端口", self.upper_port)
        form.addRow("头部 IP", self.head_ip)
        form.addRow("头部 TCP 端口", self.head_port)
        form.addRow("底盘串口", self.chassis_port)
        form.addRow("底盘波特率", self.chassis_baud)
        right_layout.addWidget(conn_box)

        gate_box = QGroupBox("安全门控")
        gate_layout = QVBoxLayout(gate_box)
        gate_layout.addWidget(self.connect_head)
        gate_layout.addWidget(self.connect_chassis)
        gate_layout.addWidget(self.run_motion)
        gate_layout.addWidget(self.run_manual)
        gate_layout.addWidget(self.run_danger)
        gate_layout.addWidget(self.run_firmware)
        right_layout.addWidget(gate_box)

        right_layout.addWidget(self.probe_button)
        right_layout.addWidget(self.summary_label)
        right_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)

        # —— 底部 ——
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        actions = QHBoxLayout()
        actions.addWidget(self.collect_button)
        actions.addWidget(self.run_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.report_button)
        actions.addStretch()
        bottom_layout.addLayout(actions)
        bottom_layout.addWidget(self.output, 1)

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.addWidget(splitter, 3)
        root_layout.addWidget(bottom, 2)
        self.setCentralWidget(central)

    def _load_cases(self) -> None:
        result = discover_by_domain(ROOT)
        self._discover = result
        self._domain_rows = result.by_domain
        self._updating_tree = True
        try:
            for domain in DOMAIN_ORDER:
                tree = self._trees[domain]
                tree.clear()
                for row in result.by_domain.get(domain, []):
                    tree.addTopLevelItem(self._make_file_item(row))
                # 更新 Tab 标题计数
                idx = DOMAIN_ORDER.index(domain)
                n = len(result.by_domain.get(domain, []))
                self.tabs.setTabText(idx, f"{DOMAIN_LABELS[domain]} ({n})")
        finally:
            self._updating_tree = False

        if result.unmarked_paths:
            self.output.appendPlainText(
                "警告：以下文件无域 marker，未进入三域树：\n"
                + "\n".join(f"  - {p}" for p in result.unmarked_paths)
                + "\n"
            )
        total = sum(len(v) for v in result.by_domain.values())
        self.output.appendPlainText(f"已加载 {total} 个接口文件（头部/上半身/底盘）。\n")
        self._refresh_summary()

    def _make_file_item(self, row: DomainModuleRow) -> QTreeWidgetItem:
        text = f"{row.display_name}{row.hint_suffix()}"
        item = QTreeWidgetItem([text])
        item.setFlags(
            item.flags()
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsAutoTristate
        )
        item.setCheckState(0, Qt.CheckState.Unchecked)
        item.setData(0, _ROLE_KIND, "file")
        item.setData(0, _ROLE_DOMAIN, row.domain)
        item.setData(0, _ROLE_PATH, row.rel_path)
        item.setData(0, _ROLE_ROW, row)
        search_bits = [row.display_name, row.rel_path]
        if len(row.items) > 1:
            for ti in row.items:
                child = QTreeWidgetItem([f"{ti.label}{ti.hint_suffix()}"])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
                child.setData(0, _ROLE_KIND, "func")
                child.setData(0, _ROLE_DOMAIN, row.domain)
                child.setData(0, _ROLE_PATH, row.rel_path)
                child.setData(0, _ROLE_FUNC, ti.func_name)
                child.setData(
                    0,
                    _ROLE_SEARCH,
                    f"{row.display_name} {ti.label} {ti.func_name}".lower(),
                )
                search_bits.extend([ti.label, ti.func_name])
                item.addChild(child)
        else:
            # 单函数：不展开，勾文件即跑该函数
            only = row.items[0]
            search_bits.extend([only.label, only.func_name])
        item.setData(0, _ROLE_SEARCH, " ".join(search_bits).lower())
        item.setToolTip(0, row.rel_path)
        return item

    def _current_domain(self) -> str:
        return DOMAIN_ORDER[self.tabs.currentIndex()]

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating_tree or column != 0:
            return
        self._updating_tree = True
        try:
            kind = item.data(0, _ROLE_KIND)
            if kind == "file" and item.childCount() > 0:
                state = item.checkState(0)
                if state != Qt.CheckState.PartiallyChecked:
                    for i in range(item.childCount()):
                        item.child(i).setCheckState(0, state)
            elif kind == "func":
                parent = item.parent()
                if parent is not None:
                    self._sync_parent_check(parent)
        finally:
            self._updating_tree = False
        self._refresh_summary()

    def _sync_parent_check(self, parent: QTreeWidgetItem) -> None:
        if parent.childCount() == 0:
            return
        checked = sum(
            1
            for i in range(parent.childCount())
            if parent.child(i).checkState(0) == Qt.CheckState.Checked
        )
        if checked == 0:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked == parent.childCount():
            parent.setCheckState(0, Qt.CheckState.Checked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

    def _apply_search(self, text: str) -> None:
        needle = text.strip().lower()
        for tree in self._trees.values():
            for i in range(tree.topLevelItemCount()):
                file_item = tree.topLevelItem(i)
                self._filter_file_item(file_item, needle)

    def _filter_file_item(self, file_item: QTreeWidgetItem, needle: str) -> None:
        if not needle:
            file_item.setHidden(False)
            for i in range(file_item.childCount()):
                file_item.child(i).setHidden(False)
            return
        file_match = needle in (file_item.data(0, _ROLE_SEARCH) or "")
        any_child = False
        for i in range(file_item.childCount()):
            child = file_item.child(i)
            child_match = needle in (child.data(0, _ROLE_SEARCH) or "")
            child.setHidden(not child_match)
            any_child = any_child or child_match
        # 有子节点时：文件匹配或任一子匹配则显示文件
        if file_item.childCount() > 0:
            file_item.setHidden(not (file_match or any_child))
            if file_match and not any_child:
                for i in range(file_item.childCount()):
                    file_item.child(i).setHidden(False)
        else:
            file_item.setHidden(not file_match)

    def _select_current_domain(self) -> None:
        tree = self._trees[self._current_domain()]
        self._updating_tree = True
        try:
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                if item.isHidden():
                    continue
                item.setCheckState(0, Qt.CheckState.Checked)
                for j in range(item.childCount()):
                    child = item.child(j)
                    if not child.isHidden():
                        child.setCheckState(0, Qt.CheckState.Checked)
                if item.childCount() > 0:
                    self._sync_parent_check(item)
        finally:
            self._updating_tree = False
        self._refresh_summary()

    def _clear_current_domain(self) -> None:
        self._set_domain_checked(self._current_domain(), Qt.CheckState.Unchecked)

    def _clear_all(self) -> None:
        for domain in DOMAIN_ORDER:
            self._set_domain_checked(domain, Qt.CheckState.Unchecked)

    def _set_domain_checked(self, domain: str, state: Qt.CheckState) -> None:
        tree = self._trees[domain]
        self._updating_tree = True
        try:
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                item.setCheckState(0, state)
                for j in range(item.childCount()):
                    item.child(j).setCheckState(0, state)
        finally:
            self._updating_tree = False
        self._refresh_summary()

    def _collect_summary(self) -> SelectionSummary:
        selected: dict[str, dict[str, frozenset[str]]] = {}
        required: set[str] = set()
        has_head = False
        has_chassis = False
        for domain in DOMAIN_ORDER:
            files: dict[str, frozenset[str]] = {}
            tree = self._trees[domain]
            for i in range(tree.topLevelItemCount()):
                file_item = tree.topLevelItem(i)
                row: DomainModuleRow | None = file_item.data(0, _ROLE_ROW)
                if row is None:
                    continue
                funcs: set[str] = set()
                if file_item.childCount() == 0:
                    if file_item.checkState(0) == Qt.CheckState.Checked and row.items:
                        funcs.add(row.items[0].func_name)
                else:
                    for j in range(file_item.childCount()):
                        child = file_item.child(j)
                        if child.checkState(0) == Qt.CheckState.Checked:
                            name = child.data(0, _ROLE_FUNC)
                            if name:
                                funcs.add(name)
                if not funcs:
                    continue
                files[row.rel_path] = frozenset(funcs)
                for item in row.items:
                    if item.func_name in funcs:
                        required |= item.required_gates
                if domain == "head":
                    has_head = True
                if domain == "chassis":
                    has_chassis = True
            if files:
                selected[domain] = files
        return SelectionSummary(
            selected=selected,
            required_gates=frozenset(required),
            has_head=has_head,
            has_chassis=has_chassis,
        )

    def _refresh_summary(self) -> None:
        summary = self._collect_summary()
        domain_n = len(summary.domain_counts)
        self.summary_label.setText(
            f"已选：{summary.file_count} 文件 / {summary.func_count} 函数（跨 {domain_n} 域）"
        )

    def _connection_params(self) -> ConnectionParams:
        return ConnectionParams(
            ip=self.ip.text().strip(),
            upper_port=self.upper_port.text().strip(),
            head_ip=self.head_ip.text().strip(),
            head_port=self.head_port.text().strip(),
            chassis_port=self.chassis_port.text().strip(),
            chassis_baud=self.chassis_baud.text().strip(),
        )

    def _gate_state(self) -> GateState:
        return GateState(
            connect_head=self.connect_head.isChecked(),
            connect_chassis=self.connect_chassis.isChecked(),
            run_motion=self.run_motion.isChecked(),
            run_manual=self.run_manual.isChecked(),
            run_danger=self.run_danger.isChecked(),
            run_firmware=self.run_firmware.isChecked(),
        )

    def _busy(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def _set_running_ui(self, running: bool) -> None:
        self.collect_button.setEnabled(not running)
        self.run_button.setEnabled(not running)
        self.probe_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        # 报告按钮：非运行且已有最近结果时可点
        self.report_button.setEnabled(
            (not running) and self._last_allure_dir is not None
        )

    def _start_pytest(self, *, collect_only: bool) -> None:
        if self._busy():
            QMessageBox.warning(self, "提示", "已有进程正在运行")
            return
        summary = self._collect_summary()
        gates = self._gate_state()
        check = validate_gates(summary, gates)
        if not check.ok:
            QMessageBox.warning(self, "无法启动", check.message)
            return

        allure_dir: Path | None = None
        if not collect_only:
            allure_dir = new_allure_dir(ROOT)
            confirm = format_run_confirm(
                summary,
                gates,
                allure_dir.relative_to(ROOT).as_posix(),
            )
            reply = QMessageBox.question(
                self,
                "确认运行",
                confirm,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                # 空目录可忽略；若已创建可留着
                return

        targets = build_pytest_targets(summary, self._domain_rows)
        if not targets:
            QMessageBox.warning(self, "提示", "请先勾选要运行的测试用例。")
            return
        allure_arg = allure_dir.relative_to(ROOT) if allure_dir is not None else None
        args = build_pytest_args(
            targets,
            self._connection_params(),
            gates,
            collect_only=collect_only,
            allure_dir=allure_arg,
        )
        self._pending_allure_dir = allure_dir if not collect_only else None
        self._run_mode = "pytest"
        self._reset_decoders()
        self.output.clear()
        self.output.appendPlainText(f"> {format_command(python_executable(), args)}\n")
        self._set_running_ui(True)
        self.process.start(python_executable(), args)

    def _start_probe(self) -> None:
        if self._busy():
            QMessageBox.warning(self, "提示", "已有进程正在运行")
            return
        gates = self._gate_state()
        args = build_probe_args(
            self._connection_params(),
            connect_head=gates.connect_head,
            connect_chassis=gates.connect_chassis,
        )
        self._run_mode = "probe"
        self._pending_allure_dir = None
        self._reset_decoders()
        self.output.clear()
        self.output.appendPlainText(f"> {format_command(python_executable(), args)}\n")
        self._set_running_ui(True)
        self.process.start(python_executable(), args)

    def _stop_process(self) -> None:
        if self._busy():
            self.output.appendPlainText("\n正在停止进程（用户中止）…\n")
            self.process.kill()

    def _open_report(self) -> None:
        if self._last_allure_dir is None:
            QMessageBox.information(self, "提示", "尚无已完成的正式运行报告。")
            return
        if not self._last_allure_dir.exists():
            QMessageBox.warning(
                self,
                "提示",
                f"报告目录不存在：{self._last_allure_dir}",
            )
            return
        serve = build_allure_serve_args(self._last_allure_dir)
        if serve is None:
            QMessageBox.warning(
                self,
                "未找到 Allure",
                "未在 PATH 中找到 allure 命令。\n"
                "请安装 Allure Commandline 后重试：\n"
                "https://docs.qameta.io/allure/",
            )
            return
        exe = serve[0]
        args = serve[1:]
        self.output.appendPlainText(f"> {format_command(exe, args)}\n")
        self.allure_process.start(exe, args)

    def _reset_decoders(self) -> None:
        self._stdout_decoder = StreamDecoder()
        self._stderr_decoder = StreamDecoder()

    def _read_stdout(self) -> None:
        text = self._stdout_decoder.feed(bytes(self.process.readAllStandardOutput()))
        if text:
            self.output.insertPlainText(text)
            self.output.ensureCursorVisible()

    def _read_stderr(self) -> None:
        text = self._stderr_decoder.feed(bytes(self.process.readAllStandardError()))
        if text:
            self.output.insertPlainText(text)
            self.output.ensureCursorVisible()

    def _finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        mode = self._run_mode
        self.output.appendPlainText(f"\n进程结束，退出码：{exit_code}")
        if mode == "pytest" and self._pending_allure_dir is not None:
            self._last_allure_dir = self._pending_allure_dir
            self.output.appendPlainText(
                f"Allure 结果目录：{self._last_allure_dir.relative_to(ROOT).as_posix()}"
            )
        self._pending_allure_dir = None
        self._run_mode = None
        self._set_running_ui(False)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())
