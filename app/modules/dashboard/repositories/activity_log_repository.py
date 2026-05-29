from abc import ABC, abstractmethod
from typing import List
from app.modules.dashboard.dtos.activity_log_dto import ActivityLogDTO

class ActivityLogRepository(ABC):
    @abstractmethod
    def add_log(self, action_type: str, reference_code: str | None, description: str) -> bool:
        """Thêm mới một dòng vết sự kiện vào DB"""
        pass

    @abstractmethod
    def get_logs_by_date(self, date_str: str) -> List[ActivityLogDTO]:
        """Lấy toàn bộ danh sách sự kiện phát sinh trong ngày cụ thể"""
        pass