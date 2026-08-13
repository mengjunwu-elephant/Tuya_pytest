"""独立老化脚本配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class AgingConnectionConfig:
    upper_ip: str = "192.168.0.232"
    upper_port: int = 6500
    head_ip: str = "192.168.0.231"
    head_port: int = 6501
    chassis_port: str = "COM9"
    chassis_baud: int = 2_000_000
    debug: bool = False
    plain_return: bool = True
    apply_limits_on_init: bool = False

    @classmethod
    def from_env(cls) -> "AgingConnectionConfig":
        return cls(
            upper_ip=os.environ.get("TUYA_ROBOT_IP", cls.upper_ip).strip()
            or cls.upper_ip,
            upper_port=env_int("TUYA_ROBOT_PORT", cls.upper_port),
            head_ip=os.environ.get("TUYA_HEAD_IP", cls.head_ip).strip()
            or cls.head_ip,
            head_port=env_int("TUYA_HEAD_PORT", cls.head_port),
            chassis_port=os.environ.get(
                "TUYA_CHASSIS_PORT", cls.chassis_port
            ).strip()
            or cls.chassis_port,
            chassis_baud=env_int("TUYA_CHASSIS_BAUD", cls.chassis_baud),
            debug=env_bool("TUYA_DEBUG", cls.debug),
            plain_return=env_bool("TUYA_PLAIN_RETURN", cls.plain_return),
            apply_limits_on_init=False,
        )


@dataclass(frozen=True)
class AgingOptions:
    run_upper_motion: bool
    run_chassis_motion: bool
    run_head_motion: bool
    monitor_only: bool
    duration_hours: float
    cycle_limit: int
    upper_speed: int
    jog_speed: int
    head_speed: int
    upper_timeout: float
    jog_timeout: float
    head_timeout: float
    monitor_interval: float
    autosave_interval: float
    chassis_forward_mps: float
    chassis_rotate_rads: float
    chassis_segment_seconds: float
    report_dir: Path
    angle_tolerance: float
    coord_tolerance: float
    consecutive_failure_limit: int
    consecutive_motion_failure_limit: int
    auto_report_max_age: float
    head_animation_paths: tuple[Path, ...]
