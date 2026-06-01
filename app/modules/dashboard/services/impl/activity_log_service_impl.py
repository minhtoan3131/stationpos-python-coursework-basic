from typing import Callable, List
from app.modules.dashboard.services.activity_log_service import ActivityLogService
from app.modules.dashboard.utils.activity_log_formatter import ActivityLogFormatter

class ActivityLogServiceImpl(ActivityLogService):
    def __init__(self, uow_factory: Callable):
        self.uow_factory = uow_factory

    def log_event(self, action_type: str, reference_code: str | None, description: str) -> None:
        with self.uow_factory() as db:
            db.activity_log_repo.add_log(action_type, reference_code, description)

    def get_daily_activity_feed(self, date_str: str) -> List[str]:
        with self.uow_factory() as db:
            logs = db.activity_log_repo.get_logs_by_date(date_str)
            return [ActivityLogFormatter.format_to_ui_string(log) for log in logs]