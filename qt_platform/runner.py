# -*- coding: utf-8 -*-
"""组装 pytest / probe / allure 命令，管理 Allure 结果目录。"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from qt_platform.gate_check import GateState, SelectionSummary
from qt_platform.test_discovery import DomainModuleRow


@dataclass(frozen=True)
class ConnectionParams:
    ip: str
    upper_port: str
    head_ip: str
    head_port: str
    chassis_port: str
    chassis_baud: str


def new_allure_dir(project_root: Path, when: datetime | None = None) -> Path:
    """创建带时间戳的独立结果目录路径（不立即 mkdir，由 pytest 写入时创建亦可）。"""
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    path = project_root / "allure-results" / f"run_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_pytest_targets(
    summary: SelectionSummary,
    domain_rows: dict[str, list[DomainModuleRow]],
) -> list[str]:
    """
    将勾选转为 pytest 路径或 nodeid。
    若某文件在本次选择中覆盖该文件全部 test 函数 → 传 rel_path；
    否则传 rel_path::func_name。
    """
    row_index: dict[tuple[str, str], DomainModuleRow] = {}
    for domain, rows in domain_rows.items():
        for row in rows:
            row_index[(domain, row.rel_path)] = row

    # path -> selected func names（跨域合并同一文件）
    selected_by_path: dict[str, set[str]] = {}
    all_funcs_by_path: dict[str, frozenset[str]] = {}
    for domain, files in summary.selected.items():
        for rel_path, funcs in files.items():
            selected_by_path.setdefault(rel_path, set()).update(funcs)
            row = row_index.get((domain, rel_path))
            if row is not None:
                all_funcs_by_path[rel_path] = row.all_file_func_names

    targets: list[str] = []
    for rel_path in sorted(selected_by_path):
        selected = selected_by_path[rel_path]
        all_funcs = all_funcs_by_path.get(rel_path, frozenset(selected))
        if selected and selected == set(all_funcs):
            targets.append(rel_path)
        else:
            for func in sorted(selected):
                targets.append(f"{rel_path}::{func}")
    return targets


def build_pytest_args(
    targets: list[str],
    conn: ConnectionParams,
    gates: GateState,
    *,
    collect_only: bool,
    allure_dir: Path | None,
) -> list[str]:
    """返回传给 sys.executable 的参数列表（含 -m pytest）。"""
    args: list[str] = ["-m", "pytest", *targets, "--run-hardware"]
    if collect_only:
        args.append("--collect-only")
    elif allure_dir is not None:
        # 使用相对仓库根的 posix 路径，便于日志阅读
        args.append(f"--alluredir={allure_dir.as_posix()}")
    args.extend(
        [
            "--tuya-ip",
            conn.ip,
            "--tuya-port",
            conn.upper_port,
            "--head-ip",
            conn.head_ip,
            "--head-port",
            conn.head_port,
            "--chassis-port",
            conn.chassis_port,
            "--chassis-baud",
            conn.chassis_baud,
        ]
    )
    if gates.connect_head:
        args.append("--connect-head")
    if not gates.connect_chassis:
        args.append("--no-connect-chassis")
    if gates.run_motion:
        args.append("--run-motion")
    if gates.run_manual:
        args.append("--run-manual")
    if gates.run_danger:
        args.append("--run-danger")
    if gates.run_firmware:
        args.append("--run-firmware")
    return args


def build_probe_args(
    conn: ConnectionParams,
    *,
    connect_head: bool,
    connect_chassis: bool = True,
) -> list[str]:
    """返回 python -m qt_platform.probe 参数。"""
    args = [
        "-m",
        "qt_platform.probe",
        "--ip",
        conn.ip,
        "--port",
        conn.upper_port,
        "--head-ip",
        conn.head_ip,
        "--head-port",
        conn.head_port,
        "--chassis-port",
        conn.chassis_port,
        "--chassis-baud",
        conn.chassis_baud,
    ]
    if connect_head:
        args.append("--connect-head")
    if not connect_chassis:
        args.append("--no-connect-chassis")
    return args


def find_allure_executable() -> str | None:
    """查找 allure CLI；找不到返回 None。"""
    return shutil.which("allure")


def build_allure_serve_args(allure_dir: Path) -> list[str] | None:
    """allure serve 的可执行文件与参数；CLI 缺失时返回 None。"""
    exe = find_allure_executable()
    if not exe:
        return None
    return [exe, "serve", str(allure_dir)]


def format_command(executable: str, args: list[str]) -> str:
    return f"{executable} {' '.join(args)}"


def python_executable() -> str:
    return sys.executable
