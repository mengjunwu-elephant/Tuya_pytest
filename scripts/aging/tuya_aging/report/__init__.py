"""日志和 Excel 报告。"""

from .collector import ReportCollector
from .log_setup import attach_run_log

__all__ = ["ReportCollector", "attach_run_log"]
