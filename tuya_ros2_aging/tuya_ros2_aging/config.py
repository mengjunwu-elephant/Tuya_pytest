"""运行配置。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgingOptions:
    run_upper_motion: bool
    run_chassis_motion: bool
    run_head_motion: bool
    monitor_only: bool
    duration_hours: float
    cycle_limit: int
    upper_speed: int
    head_speed: int
    upper_timeout: float
    head_timeout: float
    monitor_interval: float
    autosave_interval: float
    chassis_forward_mps: float
    chassis_rotate_rads: float
    chassis_segment_seconds: float
    report_dir: Path
    angle_tolerance: float
    coord_tolerance: float
    consecutive_motion_failure_limit: int
    service_timeout: float
    head_animation_paths: tuple[Path, ...]
