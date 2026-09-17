#!/usr/bin/env python3
"""Tuya ROS2 老化脚本入口（本机 ROS2 环境）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tuya_ros2_aging.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
