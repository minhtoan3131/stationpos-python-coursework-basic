from abc import ABC, abstractmethod
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO

class StoreConfigService(ABC):
    @abstractmethod
    def get_store_config(self) -> StoreConfigDTO:
        """Lấy toàn bộ thông tin cấu hình cửa hàng và khổ in."""
        pass

    @abstractmethod
    def save_store_config(self, config: StoreConfigDTO) -> bool:
        """Lưu thông tin cấu hình cửa hàng mới xuống hệ thống."""
        pass