from abc import ABC, abstractmethod

class SecurityService(ABC):
    @abstractmethod
    def verify_app_pin(self, entered_pin: str) -> bool:
        """Kiểm tra mã PIN người dùng nhập vào có trùng khớp với hệ thống hay không."""
        pass

    @abstractmethod
    def change_pin(self, current_pin: str, new_pin: str, confirm_pin: str) -> bool:
        """Thực hiện đổi mã PIN bảo vệ hệ thống."""
        pass