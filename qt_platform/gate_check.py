# -*- coding: utf-8 -*-
"""根据已选用例所需 marker 与 UI 门控状态做运行前拦截。"""
from __future__ import annotations

from dataclasses import dataclass

from qt_platform.test_discovery import DOMAIN_LABELS

GATE_LABELS: dict[str, str] = {
    "motion": "允许运动测试",
    "manual": "运行人工确认测试",
    "danger": "运行高风险测试",
    "firmware": "运行固件测试",
}


@dataclass(frozen=True)
class GateState:
    connect_head: bool = False
    connect_chassis: bool = True
    run_motion: bool = False
    run_manual: bool = False
    run_danger: bool = False
    run_firmware: bool = False

    def enabled_gates(self) -> frozenset[str]:
        enabled: set[str] = set()
        if self.run_motion:
            enabled.add("motion")
        if self.run_manual:
            enabled.add("manual")
        if self.run_danger:
            enabled.add("danger")
        if self.run_firmware:
            enabled.add("firmware")
        return frozenset(enabled)


@dataclass(frozen=True)
class SelectionSummary:
    """跨域勾选摘要，供门控校验与确认框使用。"""

    # domain -> {rel_path: frozenset[func_name]}
    selected: dict[str, dict[str, frozenset[str]]]
    required_gates: frozenset[str]
    has_head: bool
    has_chassis: bool = False

    @property
    def file_count(self) -> int:
        paths: set[str] = set()
        for files in self.selected.values():
            paths.update(files)
        return len(paths)

    @property
    def func_count(self) -> int:
        return sum(len(funcs) for files in self.selected.values() for funcs in files.values())

    @property
    def domain_counts(self) -> dict[str, int]:
        return {d: len(files) for d, files in self.selected.items() if files}

    def is_empty(self) -> bool:
        return self.func_count == 0


@dataclass(frozen=True)
class GateCheckResult:
    ok: bool
    errors: tuple[str, ...] = ()

    @property
    def message(self) -> str:
        return "\n".join(self.errors)


def validate_gates(summary: SelectionSummary, state: GateState) -> GateCheckResult:
    """运行/仅收集前校验：已选非空、门控齐全、头部需连接。"""
    errors: list[str] = []
    if summary.is_empty():
        errors.append("请先勾选要运行的测试用例。")
        return GateCheckResult(ok=False, errors=tuple(errors))

    enabled = state.enabled_gates()
    gate_order = ("motion", "manual", "danger", "firmware")
    missing = sorted(
        summary.required_gates - enabled,
        key=lambda g: gate_order.index(g) if g in gate_order else 99,
    )
    if missing:
        names = "、".join(GATE_LABELS.get(g, g) for g in missing)
        errors.append(f"已选用例需要以下门控，请先勾选：{names}")

    if summary.has_head and not state.connect_head:
        errors.append("已选包含头部用例，请勾选「连接头部」。")

    if summary.has_chassis and not state.connect_chassis:
        errors.append("已选包含底盘用例，请勾选「连接底盘」。")

    return GateCheckResult(ok=not errors, errors=tuple(errors))


def format_run_confirm(summary: SelectionSummary, state: GateState, allure_dir: str | None) -> str:
    """运行测试确认摘要文案。"""
    lines: list[str] = ["即将运行以下测试：", ""]
    domain_parts: list[str] = []
    for domain in ("head", "upper_body", "chassis"):
        n = len(summary.selected.get(domain, {}))
        if n:
            domain_parts.append(f"{DOMAIN_LABELS[domain]} {n}")
    lines.append("域：" + " / ".join(domain_parts) if domain_parts else "域：无")
    lines.append(f"文件数：{summary.file_count}")
    lines.append(f"函数数：{summary.func_count}")

    enabled = ["真机 hardware"]
    if state.connect_head:
        enabled.append("连接头部")
    if state.connect_chassis:
        enabled.append("连接底盘")
    for gate in ("motion", "manual", "danger", "firmware"):
        if gate in state.enabled_gates():
            enabled.append(GATE_LABELS[gate])
    lines.append("将启用：" + "、".join(enabled))
    if allure_dir:
        lines.append(f"Allure 目录：{allure_dir}")
    lines.append("")
    lines.append("确认开始运行？")
    return "\n".join(lines)
