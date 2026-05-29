from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.constants.setting_key import SettingKey
from app.modules.setting.services.StoreConfigService import StoreConfigService


class StoreConfigServiceImpl(StoreConfigService):
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def get_store_config(self) -> StoreConfigDTO:
        with self.uow_factory() as uow:
            # Lấy Dictionary chuỗi thô từ Database
            settings = uow.setting_repo.get_all_settings()

            # Sử dụng Enum để truy xuất giá trị an toàn từ dictionary
            return StoreConfigDTO(
                name=settings.get(SettingKey.STORE_NAME.value, 'Văn phòng phẩm'),
                phone=settings.get(SettingKey.STORE_PHONE.value, ''),
                address=settings.get(SettingKey.STORE_ADDRESS.value, 'Hà Nội'),
                paper_size=settings.get(SettingKey.PRINT_PAPER_SIZE.value, 'K80'),
                footer=settings.get(SettingKey.RECEIPT_FOOTER.value, 'Cảm ơn quý khách, hẹn gặp lại!')
            )

    def save_store_config(self, config: StoreConfigDTO) -> bool:
        with self.uow_factory() as uow:
            # Ép chặt Key thông qua Enum khi gọi tầng Repo cập nhật dữ liệu dưới DB
            uow.setting_repo.update_setting(SettingKey.STORE_NAME.value, config.name)
            uow.setting_repo.update_setting(SettingKey.STORE_PHONE.value, config.phone)
            uow.setting_repo.update_setting(SettingKey.STORE_ADDRESS.value, config.address)
            uow.setting_repo.update_setting(SettingKey.PRINT_PAPER_SIZE.value, config.paper_size)
            uow.setting_repo.update_setting(SettingKey.RECEIPT_FOOTER.value, config.footer)
            return True