from abc import ABC, abstractmethod
from typing import List

class ActivityLogService(ABC):
    @abstractmethod
    def log_event(self, action_type: str, reference_code: str | None, description: str) -> None:
        """API chung cho toàn hệ thống gọi để lưu log hành vi kiểm toán"""
        pass

    @abstractmethod
    def get_daily_activity_feed(self, date_str: str) -> List[str]:
        """API cho Dashboard gọi lấy chuỗi text Timeline hiển thị lên UI"""
        pass