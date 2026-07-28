#!/usr/bin/env python
"""TuyaRobot 独立老化脚本兼容入口。"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tuya_aging.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
