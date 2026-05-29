from abc import ABC, abstractmethod
from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO

class BackupService(ABC):
    @abstractmethod
    def get_backup_config(self) -> BackupConfigDTO:
        """Lấy thông số cấu hình sao lưu hiện tại."""
        pass

    @abstractmethod
    def save_backup_config(self, config: BackupConfigDTO) -> bool:
        """Lưu thông số cấu hình sao lưu hệ thống."""
        pass

    @abstractmethod
    def execute_backup(self) -> str:
        """Gọi mysqldump để xuất file backup. Trả về đường dẫn file .sql thành công."""
        pass

    @abstractmethod
    def execute_restore(self, file_path: str) -> bool:
        """Gọi mysql client để khôi phục cấu trúc và dữ liệu từ file .sql."""
        pass