"""本次老化运行日志配置。"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    from common1 import logger
except Exception:  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(asctime)s [%(filename)s:%(lineno)d] %(message)s",
    )
    logger = logging.getLogger("tuya_robot_aging")


def attach_run_log(report_root: Path) -> None:
    log_path = report_root / "aging.log"
    resolved = str(log_path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(
            handler, "baseFilename", ""
        ) == resolved:
            return
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            "%(levelname)s %(asctime)s "
            "[%(threadName)s %(filename)s:%(lineno)d] %(message)s"
        )
    )
    logger.addHandler(handler)
