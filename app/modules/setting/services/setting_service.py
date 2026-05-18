from abc import ABC, abstractmethod

class SettingService(ABC):
    @abstractmethod
    def verify_app_pin(self, entered_pin: str) -> bool:
        """Kiểm tra mã PIN người dùng nhập vào có trùng khớp với mã trong hệ thống hay không."""
        pass