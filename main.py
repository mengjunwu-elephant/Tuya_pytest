# -*- coding: utf-8 -*-
"""TuyaRobot 自动化测试命令行入口。"""
from __future__ import annotations

import argparse

import pytest

from settings import CASES_DIR, REPORT_DIR


MODULES = {
    "all": [CASES_DIR["1"], CASES_DIR["2"], CASES_DIR["3"]],
    "robot": [CASES_DIR["1"]],
    "upper_body": [CASES_DIR["2"]],
    "chassis": [CASES_DIR["3"]],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="TuyaRobot 自动化测试")
    parser.add_argument("--module", choices=MODULES, default="all")
    parser.add_argument("--marker", default=None, help="pytest marker 表达式")
    parser.add_argument("--allure", action="store_true", help="生成 Allure 原始结果")
    args, pytest_args = parser.parse_known_args()

    command = ["-s", *MODULES[args.module]]
    if args.marker:
        command.extend(["-m", args.marker])
    if args.allure:
        command.append(f"--alluredir={REPORT_DIR}")
    command.extend(pytest_args)
    return pytest.main(command)


if __name__ == "__main__":
    raise SystemExit(main())
