from app.modules.setting.services.setting_service import SettingService

class SettingServiceImpl(SettingService):
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def verify_app_pin(self, entered_pin: str) -> bool:
        with self.uow_factory() as uow:
            settings = uow.setting_repo.get_all_settings()
            # Lấy mã PIN hiện tại dưới DB, mặc định nếu chưa có là '1234'
            current_pin = settings.get('APP_PIN', '1234')
            return current_pin == entered_pin