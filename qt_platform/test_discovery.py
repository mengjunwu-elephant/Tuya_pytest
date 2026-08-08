# -*- coding: utf-8 -*-
"""扫描 test_*.py，解析接口表名、test 函数、pytest marker；按域分组供 QT 勾选。"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

_SHEET_RE = re.compile(
    r'get_test_data_from_excel\s*\(\s*[^,]+,\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)
# 文件名 test_12_xxx.py 按数字 12 排序，避免字符串顺序下 test_10 排在 test_2 前
_TEST_FILE_NUM = re.compile(r"test_(\d+)_", re.IGNORECASE)

DOMAIN_ORDER: tuple[str, ...] = ("head", "upper_body", "chassis")
DOMAIN_LABELS: dict[str, str] = {
    "head": "头部",
    "upper_body": "上半身",
    "chassis": "底盘",
}
GATE_MARKERS: frozenset[str] = frozenset({"motion", "manual", "danger", "firmware"})
DOMAIN_MARKERS: frozenset[str] = frozenset({"head", "upper_body", "chassis"})
_SCAN_ROOTS: tuple[str, ...] = ("testcases/upper_body", "testcases/chassis")
GATE_HINTS: dict[str, str] = {
    "motion": "运动",
    "manual": "人工",
    "danger": "高风险",
    "firmware": "固件",
}


@dataclass(frozen=True)
class TestItem:
    """单个可运行测试项：对应一个 test_* 函数。"""

    func_name: str
    label: str  # 界面展示（通常来自 @allure.story）
    uses_input: bool = False  # 函数体内是否调用 input()（需人工交互）
    markers: frozenset[str] = frozenset()

    @property
    def domain(self) -> str | None:
        return domain_for_markers(self.markers)

    @property
    def required_gates(self) -> frozenset[str]:
        return self.markers & GATE_MARKERS

    def hint_suffix(self) -> str:
        parts: list[str] = []
        for key in ("motion", "manual", "danger", "firmware"):
            if key in self.markers:
                parts.append(GATE_HINTS[key])
        if self.uses_input:
            parts.append("交互")
        if not parts:
            return ""
        return " [" + "/".join(parts) + "]"


@dataclass
class TestModuleRow:
    """单行：一个测试文件，内含若干测试项（按源码顺序）。"""

    rel_path: str  # posix 相对项目根
    display_name: str  # 表名或推导名
    items: list[TestItem] = field(default_factory=list)

    def choice_uses_input(self, choice: str) -> bool:
        """当前选择的测试项是否包含 input()（含「全部」时任一函数含即 True）。"""
        if choice == "__ALL__":
            return any(i.uses_input for i in self.items)
        for i in self.items:
            if i.func_name == choice:
                return i.uses_input
        return False

    def pytest_k_expr_for(self, choice: str) -> str | None:
        """
        choice: 某 TestItem.func_name，或 "__ALL__" 表示本文件全部 test 函数。
        返回传给 pytest -k 的表达式。
        """
        names = [i.func_name for i in self.items]
        if not names:
            return None
        if choice == "__ALL__":
            return names[0] if len(names) == 1 else " or ".join(names)
        if choice in names:
            return choice
        return None

    @property
    def required_gates(self) -> frozenset[str]:
        gates: set[str] = set()
        for item in self.items:
            gates |= item.required_gates
        return frozenset(gates)

    @property
    def all_func_names(self) -> frozenset[str]:
        return frozenset(i.func_name for i in self.items)


@dataclass
class DomainModuleRow:
    """某一测试域下的一个文件视图（可能只含该域内的函数）。"""

    domain: str
    rel_path: str
    display_name: str
    items: list[TestItem] = field(default_factory=list)
    all_file_func_names: frozenset[str] = frozenset()

    @property
    def required_gates(self) -> frozenset[str]:
        gates: set[str] = set()
        for item in self.items:
            gates |= item.required_gates
        return frozenset(gates)

    @property
    def domain_func_names(self) -> frozenset[str]:
        return frozenset(i.func_name for i in self.items)

    def hint_suffix(self) -> str:
        gates = self.required_gates
        parts = [GATE_HINTS[k] for k in ("motion", "manual", "danger", "firmware") if k in gates]
        if any(i.uses_input for i in self.items):
            parts.append("交互")
        if not parts:
            return ""
        return " [" + "/".join(parts) + "]"


@dataclass
class DiscoverResult:
    """三域发现结果。"""

    by_domain: dict[str, list[DomainModuleRow]]
    unmarked_paths: list[str] = field(default_factory=list)


def domain_for_markers(markers: frozenset[str] | set[str]) -> str | None:
    """域归属优先级：head > chassis > upper_body。"""
    if "head" in markers:
        return "head"
    if "chassis" in markers:
        return "chassis"
    if "upper_body" in markers:
        return "upper_body"
    return None


def _string_from_ast_constant(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    str_node = getattr(ast, "Str", None)
    if str_node is not None and isinstance(node, str_node):
        return getattr(node, "s", None)
    return None


def _allure_story_label(decorator_list: list[ast.expr]) -> str | None:
    """匹配 @allure.story("标题")。"""
    for dec in decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        func = dec.func
        if not isinstance(func, ast.Attribute) or func.attr != "story":
            continue
        if not isinstance(func.value, ast.Name):
            continue
        if func.value.id != "allure":
            continue
        if not dec.args:
            continue
        s = _string_from_ast_constant(dec.args[0])
        if s is not None:
            return s.strip() or None
    return None


def _pytest_mark_names(decorator_list: list[ast.expr]) -> frozenset[str]:
    """解析 @pytest.mark.xxx / @pytest.mark.xxx(...)。"""
    names: set[str] = set()
    for dec in decorator_list:
        node = dec
        if isinstance(node, ast.Call):
            node = node.func
        # pytest.mark.name
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
            if (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id == "pytest"
                and node.value.attr == "mark"
            ):
                names.add(node.attr)
                continue
        # mark.name（from pytest import mark）较少见，忽略
    return frozenset(names)


_OPERATOR_PROMPT_FUNCS = frozenset({"input", "prompt_continue", "prompt_text"})


def _tree_uses_operator_input(tree: ast.AST) -> bool:
    """检测模块/函数内是否调用 input 或 operator_input 封装。"""
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id in _OPERATOR_PROMPT_FUNCS:
                return True
    return False


def _label_for_test_function(name: str, story: str | None, used_base: dict[str, int]) -> str:
    base = (story or "").strip() or name
    n = used_base.get(base, 0)
    used_base[base] = n + 1
    if n == 0:
        return base
    return f"{base} ({name})"


def discover_under_root(project_root: Path, testcase_root: str) -> list[TestModuleRow]:
    project_root = project_root.resolve()
    root = (project_root / testcase_root).resolve()
    if not root.is_dir():
        return []
    rows: list[TestModuleRow] = []
    for p in sorted(root.glob("test_*.py")):
        if p.name == "conftest.py":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        m = _SHEET_RE.search(text)
        display = m.group(1) if m else _sheet_from_stem(p.stem)
        try:
            tree = ast.parse(text, filename=str(p))
        except SyntaxError:
            continue
        used: dict[str, int] = {}
        items: list[TestItem] = []
        file_uses_input = _tree_uses_operator_input(tree)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if not node.name.startswith("test_"):
                continue
            story = _allure_story_label(node.decorator_list)
            label = _label_for_test_function(node.name, story, used)
            uses_in = file_uses_input or _tree_uses_operator_input(node)
            markers = _pytest_mark_names(node.decorator_list)
            items.append(
                TestItem(
                    func_name=node.name,
                    label=label,
                    uses_input=uses_in,
                    markers=markers,
                ),
            )
        if not items:
            continue
        rel = p.relative_to(project_root).as_posix()
        rows.append(
            TestModuleRow(rel_path=rel, display_name=display, items=items),
        )
    rows.sort(key=lambda r: _pytest_file_sort_key(r.rel_path))
    return rows


def _sheet_from_stem(stem: str) -> str:
    # test_1_get_system_version -> get_system_version
    if stem.startswith("test_"):
        rest = stem[5:]
        parts = rest.split("_", 1)
        if len(parts) == 2 and parts[0].isdigit():
            return parts[1]
        return rest
    return stem


def _pytest_file_sort_key(rel_posix: str) -> tuple[int, int, str]:
    """同一目录内：优先按 test_<数字>_ 中的数字升序，其余按文件名。"""
    name = Path(rel_posix).name
    m = _TEST_FILE_NUM.search(name)
    if m:
        return (0, int(m.group(1)), name.lower())
    return (1, 0, name.lower())


def discover_for_arm(project_root: Path, testcase_roots: list[str]) -> list[TestModuleRow]:
    """扁平列表（跨根去重），顺序为 arms 中 testcase_roots 顺序 + 组内数字序。"""
    seen: set[str] = set()
    out: list[TestModuleRow] = []
    for tr in testcase_roots:
        for row in discover_under_root(project_root, tr):
            if row.rel_path in seen:
                continue
            seen.add(row.rel_path)
            out.append(row)
    return out


def discover_grouped_for_arm(
    project_root: Path, testcase_roots: list[str]
) -> list[tuple[str, list[TestModuleRow]]]:
    """按测试域分组；组内按 test_ 后数字排序，并跨组去重路径。"""
    seen: set[str] = set()
    groups: list[tuple[str, list[TestModuleRow]]] = []
    for tr in testcase_roots:
        chunk: list[TestModuleRow] = []
        for row in discover_under_root(project_root, tr):
            if row.rel_path in seen:
                continue
            seen.add(row.rel_path)
            chunk.append(row)
        if chunk:
            groups.append((tr, chunk))
    return groups


def discover_by_domain(project_root: Path) -> DiscoverResult:
    """
    扫描上半身与底盘目录，按 pytest.mark 拆成头部 / 上半身 / 底盘。
    无域 marker 的文件进入 unmarked_paths，不进入三域树。
    """
    project_root = project_root.resolve()
    by_domain: dict[str, list[DomainModuleRow]] = {d: [] for d in DOMAIN_ORDER}
    unmarked: list[str] = []
    seen: set[str] = set()

    for root in _SCAN_ROOTS:
        for row in discover_under_root(project_root, root):
            if row.rel_path in seen:
                continue
            seen.add(row.rel_path)
            grouped: dict[str, list[TestItem]] = {}
            for item in row.items:
                domain = item.domain
                if domain is None:
                    continue
                grouped.setdefault(domain, []).append(item)
            if not grouped:
                unmarked.append(row.rel_path)
                continue
            all_funcs = row.all_func_names
            for domain, items in grouped.items():
                by_domain[domain].append(
                    DomainModuleRow(
                        domain=domain,
                        rel_path=row.rel_path,
                        display_name=row.display_name,
                        items=items,
                        all_file_func_names=all_funcs,
                    )
                )

    for domain in DOMAIN_ORDER:
        by_domain[domain].sort(key=lambda r: _pytest_file_sort_key(r.rel_path))
    return DiscoverResult(by_domain=by_domain, unmarked_paths=unmarked)
