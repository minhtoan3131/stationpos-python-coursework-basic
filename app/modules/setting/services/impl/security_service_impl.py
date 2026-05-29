from app.modules.setting.services.security_service import SecurityService
from app.modules.setting.constants.setting_key import SettingKey


class SecurityServiceImpl(SecurityService):
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    def verify_app_pin(self, entered_pin: str) -> bool:
        with self.uow_factory() as uow:
            settings = uow.setting_repo.get_all_settings()
            # Sử dụng định danh Enum chuẩn hóa, mặc định là '1234' nếu cài mới
            current_pin = settings.get(SettingKey.APP_PIN.value, '1234')
            return current_pin == entered_pin

    def change_pin(self, current_pin: str, new_pin: str, confirm_pin: str) -> bool:
        # Kiểm tra các trường thông tin rỗng
        if not current_pin or not new_pin or not confirm_pin:
            raise ValueError("Vui lòng nhập đầy đủ tất cả các ô mã PIN!")

        # Tầng 2: Kiểm tra độ dài và định dạng mã PIN mới (Yêu cầu từ 4-6 chữ số)
        if not (4 <= len(new_pin) <= 6) or not new_pin.isdigit():
            raise ValueError("Mã PIN mới phải có độ dài từ 4 đến 6 chữ số và chỉ chứa ký tự số!")

        # Tầng 3: Kiểm tra tính trùng khớp của mã PIN mới
        if new_pin != confirm_pin:
            raise ValueError("Xác nhận mã PIN mới không khớp, vui lòng kiểm tra lại!")

        with self.uow_factory() as uow:
            # Tải cấu hình hiện tại lên để đối chiếu
            settings = uow.setting_repo.get_all_settings()
            db_current_pin = settings.get(SettingKey.APP_PIN.value, '1234')

            # Tầng 4: Kiểm tra mã PIN cũ nhập vào có khớp với Database không
            if db_current_pin != current_pin:
                raise ValueError("Mã PIN hiện tại không chính xác!")

            # Tầng 5: Ghi nhận mã PIN mới xuống cơ sở dữ liệu
            uow.setting_repo.update_setting(SettingKey.APP_PIN.value, new_pin)

            uow.activity_log_repo.add_log(
                action_type='SYSTEM',
                reference_code='SECURITY',
                description="Thay đổi mã PIN bảo mật hệ thống thành công"
            )
            return True