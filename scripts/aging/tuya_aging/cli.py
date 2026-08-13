"""命令行参数、配置校验和程序入口。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Sequence

from . import constants
from .config import AgingConnectionConfig, AgingOptions
from .report import ReportCollector, attach_run_log
from .report.log_setup import logger
from .runtime.coordinator import AgingCoordinator


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HEAD_ANIMATION_DIR = Path(__file__).resolve().parent / "pag_file"


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须为正整数")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("不得小于 0")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return parsed


def discover_pag_files(directory: Path) -> tuple[Path, ...]:
    """扫描目录下全部 .pag；目录不存在或为空则返回空元组。"""
    if not directory.is_dir():
        return ()
    return tuple(sorted(path.resolve() for path in directory.glob("*.pag")))


def build_parser() -> argparse.ArgumentParser:
    defaults = AgingConnectionConfig.from_env()
    parser = argparse.ArgumentParser(
        description=(
            "TuyaRobot 上半身、头部与底盘独立并行老化。"
            "软件限位和 Jog 属于危险实机运动，必须现场人工监护。"
        )
    )
    parser.add_argument("--upper-ip", default=defaults.upper_ip)
    parser.add_argument(
        "--upper-port", type=positive_int, default=defaults.upper_port
    )
    parser.add_argument("--head-ip", default=defaults.head_ip)
    parser.add_argument(
        "--head-port", type=positive_int, default=defaults.head_port
    )
    parser.add_argument("--chassis-port", default=defaults.chassis_port)
    parser.add_argument(
        "--chassis-baud",
        type=positive_int,
        default=defaults.chassis_baud,
    )
    parser.add_argument(
        "--run-upper-motion",
        action="store_true",
        help="启用上半身真实运动、软件限位和 Jog 老化",
    )
    parser.add_argument(
        "--run-head-motion",
        action="store_true",
        help="启用头部真实运动、软件限位、四色 LED 与 pag 动画老化",
    )
    parser.add_argument(
        "--run-chassis-motion",
        action="store_true",
        help="启用底盘真实往返及旋转运动",
    )
    parser.add_argument(
        "--monitor-only",
        action="store_true",
        help="仅采集上半身、头部和底盘状态，不执行运动",
    )
    parser.add_argument(
        "--duration-hours",
        type=float,
        default=0.0,
        help="运行小时数，0 表示不限时",
    )
    parser.add_argument(
        "--cycle-limit",
        type=non_negative_int,
        default=0,
        help="每个运动子系统最大循环数，0 表示不限次数",
    )
    parser.add_argument("--upper-speed", type=positive_int, default=20)
    parser.add_argument("--jog-speed", type=positive_int, default=10)
    parser.add_argument(
        "--head-speed",
        type=positive_int,
        default=constants.HEAD_SPEED,
        help="头部运动速度（SDK 1~100）",
    )
    parser.add_argument(
        "--upper-timeout", type=positive_float, default=60.0
    )
    parser.add_argument(
        "--jog-timeout", type=positive_float, default=300.0
    )
    parser.add_argument(
        "--head-timeout", type=positive_float, default=60.0
    )
    parser.add_argument(
        "--monitor-interval", type=positive_float, default=0.5
    )
    parser.add_argument(
        "--autosave-interval", type=positive_float, default=60.0
    )
    parser.add_argument(
        "--chassis-forward-mps", type=positive_float, default=0.05
    )
    parser.add_argument(
        "--chassis-rotate-rads", type=positive_float, default=0.1
    )
    parser.add_argument(
        "--chassis-segment-seconds", type=positive_float, default=2.0
    )
    parser.add_argument(
        "--angle-tolerance", type=positive_float, default=0.1
    )
    parser.add_argument(
        "--coord-tolerance", type=positive_float, default=1.0
    )
    parser.add_argument(
        "--consecutive-failure-limit", type=positive_int, default=3
    )
    parser.add_argument(
        "--consecutive-motion-failure-limit",
        type=positive_int,
        default=10,
        help="连续运动指令无响应或运动未成功的停止阈值",
    )
    parser.add_argument(
        "--auto-report-max-age", type=positive_float, default=1.0
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPO_ROOT / "test_report" / "aging",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="只校验参数和内置角度/坐标/头部限位，不连接设备",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=defaults.debug,
    )
    parser.add_argument(
        "--plain-return",
        action=argparse.BooleanOptionalAction,
        default=defaults.plain_return,
    )
    return parser


def validate_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    if args.monitor_only and (
        args.run_upper_motion
        or args.run_chassis_motion
        or args.run_head_motion
    ):
        parser.error("--monitor-only 不能与运动开关同时使用")
    if not 1 <= args.upper_speed <= 100:
        parser.error("--upper-speed 必须在 1~100")
    if not 1 <= args.jog_speed <= 100:
        parser.error("--jog-speed 必须在 1~100")
    if not 1 <= args.head_speed <= 100:
        parser.error("--head-speed 必须在 1~100")
    if args.duration_hours < 0:
        parser.error("--duration-hours 不得小于 0")
    for group in constants.ANGLE_GROUPS:
        if len(group["left"]) != 8 or len(group["right"]) != 8:
            parser.error("内置全关节角度组长度错误")
    for group in constants.COORD_GROUPS:
        if len(group["left"]) != 6 or len(group["right"]) != 6:
            parser.error("内置全坐标组长度错误")
    if len(constants.HEAD_ZERO_ANGLES) != 4:
        parser.error("头部零位长度错误")
    if sorted(constants.HEAD_JOINT_SOFT_LIMITS) != [1, 2, 3, 4]:
        parser.error("头部软限位关节号错误")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_args(args, parser)
    animation_paths = discover_pag_files(DEFAULT_HEAD_ANIMATION_DIR)
    connection = AgingConnectionConfig(
        upper_ip=args.upper_ip,
        upper_port=args.upper_port,
        head_ip=args.head_ip,
        head_port=args.head_port,
        chassis_port=args.chassis_port,
        chassis_baud=args.chassis_baud,
        debug=args.debug,
        plain_return=args.plain_return,
        apply_limits_on_init=False,
    )
    if args.validate_config:
        print(
            json.dumps(
                {
                    "connection": asdict(connection),
                    "angle_groups": constants.ANGLE_GROUPS,
                    "coord_groups": constants.COORD_GROUPS,
                    "joint_soft_limits": constants.JOINT_SOFT_LIMITS,
                    "coord_soft_limits": constants.COORD_SOFT_LIMITS,
                    "head_joint_soft_limits": constants.HEAD_JOINT_SOFT_LIMITS,
                    "head_zero_angles": constants.HEAD_ZERO_ANGLES,
                    "head_animation_dir": str(DEFAULT_HEAD_ANIMATION_DIR),
                    "head_animation_paths": [
                        str(path) for path in animation_paths
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if not (
        args.monitor_only
        or args.run_upper_motion
        or args.run_chassis_motion
        or args.run_head_motion
    ):
        parser.error(
            "必须选择 --monitor-only、--run-upper-motion、"
            "--run-head-motion 或 --run-chassis-motion"
        )
    options = AgingOptions(
        run_upper_motion=args.run_upper_motion,
        run_chassis_motion=args.run_chassis_motion,
        run_head_motion=args.run_head_motion,
        monitor_only=args.monitor_only,
        duration_hours=args.duration_hours,
        cycle_limit=args.cycle_limit,
        upper_speed=args.upper_speed,
        jog_speed=args.jog_speed,
        head_speed=args.head_speed,
        upper_timeout=args.upper_timeout,
        jog_timeout=args.jog_timeout,
        head_timeout=args.head_timeout,
        monitor_interval=args.monitor_interval,
        autosave_interval=args.autosave_interval,
        chassis_forward_mps=args.chassis_forward_mps,
        chassis_rotate_rads=args.chassis_rotate_rads,
        chassis_segment_seconds=args.chassis_segment_seconds,
        report_dir=args.report_dir,
        angle_tolerance=args.angle_tolerance,
        coord_tolerance=args.coord_tolerance,
        consecutive_failure_limit=args.consecutive_failure_limit,
        consecutive_motion_failure_limit=(
            args.consecutive_motion_failure_limit
        ),
        auto_report_max_age=args.auto_report_max_age,
        head_animation_paths=animation_paths,
    )
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_root = options.report_dir.resolve() / run_id
    report = ReportCollector(
        report_root,
        {
            **asdict(connection),
            **{
                key: (
                    [str(item) for item in value]
                    if key == "head_animation_paths"
                    else (str(value) if isinstance(value, Path) else value)
                )
                for key, value in asdict(options).items()
            },
        },
    )
    attach_run_log(report_root)
    logger.info("TuyaRobot 老化启动，报告目录：%s", report_root)
    logger.warning(
        "上半身软件限位、头部软限位、Jog 和底盘运动必须由现场人员持续监护"
    )
    try:
        coordinator = AgingCoordinator(connection, options, report)
        return coordinator.run()
    except Exception as exc:
        logger.exception("老化脚本启动或运行失败")
        report.event("FATAL", "主程序", "启动/运行", str(exc), exc)
        report.save()
        return 1
