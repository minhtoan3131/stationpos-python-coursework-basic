from abc import ABC, abstractmethod
from typing import Dict

class SettingRepository(ABC):
    @abstractmethod
    def get_all_settings(self) -> Dict[str, str]:
        """Lấy toàn bộ cấu hình dưới dạng Dictionary {KEY: VALUE} để UI dễ dàng bind dữ liệu."""
        pass

    @abstractmethod
    def update_setting(self, key: str, new_value: str) -> bool:
        """Cập nhật giá trị mới cho một cấu hình cụ thể."""
        pass