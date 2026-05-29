import pytest
from PyQt6.QtCore import Qt

from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.ui.controllers.setting_management_controller import SettingManagementController


# ==============================================================================
# PYTEST FIXTURES (Cô lập hoàn toàn hạ tầng bằng Mock)
# ==============================================================================

@pytest.fixture
def mock_store_config_service(mocker):
    """Làm giả dịch vụ thông tin cửa hàng phục vụ hàm load màn hình chính"""
    service = mocker.Mock()
    service.get_store_config.return_value = StoreConfigDTO(
        name="Văn phòng phẩm ABC", phone="0901234567", address="Hà Nội",
        paper_size="K80", footer="Cảm ơn quý khách!"
    )
    return service


@pytest.fixture
def mock_backup_service(mocker):
    """Làm giả dịch vụ sao lưu cấu hình"""
    service = mocker.Mock()
    service.get_backup_config.return_value = BackupConfigDTO(
        auto_enabled=False, backup_time="22:00", folder_path="/Users/test/Backup"
    )
    return service


@pytest.fixture
def mock_security_service(mocker):
    """Làm giả cổng nghiệp vụ SecurityService để kiểm thử tương tác chỉ lệnh"""
    return mocker.Mock()


@pytest.fixture
def ui_window(qtbot, mock_store_config_service, mock_security_service, mock_backup_service):
    """Khởi tạo Controller Giao diện, đăng ký vòng đời với qtbot và nạp dữ liệu gốc"""
    window = SettingManagementController(
        store_config_service=mock_store_config_service,
        security_service=mock_security_service,
        backup_service=mock_backup_service
    )
    qtbot.addWidget(window)  # Đăng ký widget để quản lý giải phóng bộ nhớ RAM
    window.load_current_settings()  # Đổ dữ liệu nền ban đầu lên hệ thống

    # Ép buộc hiển thị giao diện để tính toán cấu trúc pixel hình học
    window.show()
    return window


# ==============================================================================
# UI TEST CASES (Đã đồng bộ hóa 100% với hành vi ứng dụng thực tế)
# ==============================================================================

def test_initial_security_ui_state_should_be_clean_and_keep_save_button_enabled(ui_window):
    """
    KỊCH BẢN 1: Mở tab Bảo mật thiết lập mã PIN
     Khẳng định nút btn_save_security mặc định luôn SÁNG RÕ (True) để thu ngân bấm bất cứ lúc nào.
    """
    # THEN: Xác minh trạng thái hiển thị mặc định sạch sẽ của các ô nhập mật mã
    assert ui_window.ui.txt_pin_hientai.text() == ""
    assert ui_window.ui.txt_pin_moi.text() == ""
    assert ui_window.ui.txt_pin_xacnhan.text() == ""

    #  Nút bảo mật luôn sẵn sàng nhận lệnh bấm
    assert ui_window.ui.btn_save_security.isEnabled() is True


def test_pin_fields_modification_should_maintain_save_button_enabled(ui_window):
    """
    KỊCH BẢN 2: Người dùng điền thông tin vào các ô mật mã trên Form
    - Kỳ vọng: Vì không thuộc nhóm cấu hình bẩn, nút Đổi mã PIN luôn giữ nguyên trạng thái kích hoạt.
    """
    assert ui_window.ui.btn_save_security.isEnabled() is True

    # WHEN: Thay đổi text an toàn, phòng chống lỗi crash driver bàn phím trên macOS
    ui_window.ui.txt_pin_hientai.setText("1234")
    ui_window.ui.txt_pin_moi.setText("5678")
    ui_window.ui.txt_pin_xacnhan.setText("5678")

    # THEN: Nút cập nhật mã PIN vẫn giữ nguyên trạng thái kích hoạt sẵn sàng
    assert ui_window.ui.btn_save_security.isEnabled() is True


def test_handle_change_pin_successfully_should_invoke_service_and_clear_fields(mocker, ui_window,
                                                                               mock_security_service):
    """
    KỊCH BẢN 3: Thu ngân thực hiện quy trình Thay đổi mã PIN chuẩn xác và thành công
     Gọi assert_called_once_with dạng tham số vị trí (Positional Args) khớp với Controller.
    """
    # GIVEN: Điền thông số đổi mã PIN hợp lệ
    ui_window.ui.txt_pin_hientai.setText("1234")
    ui_window.ui.txt_pin_moi.setText("5678")
    ui_window.ui.txt_pin_xacnhan.setText("5678")
    assert ui_window.ui.btn_save_security.isEnabled() is True

    # PATCH POPUP & SERVICE: Đánh chặn hộp thoại thông báo tránh treo luồng test
    mock_info_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.information")
    mock_security_service.change_pin.return_value = True

    # WHEN: Thực hiện bấm lệnh đổi mã PIN
    ui_window.ui.btn_save_security.click()

    # THEN:
     So khớp chính xác 3 chuỗi mật mã truyền dạng tham số vị trí theo đúng thực tế
    mock_security_service.change_pin.assert_called_once_with("1234", "5678", "5678")

    # 2. Hộp thoại Popup thông báo đổi khóa an toàn thành công phải bắn lên
    mock_info_box.assert_called_once_with(
        ui_window,
        "Thành công",
        "Đã cập nhật mã PIN bảo mật hệ thống mới thành công!"
    )
    # 3. ĐẢM BẢO TRẠNG THÁI: Tự động xóa trống các ô nhập để bảo mật thông tin sau khi lưu
    assert ui_window.ui.txt_pin_hientai.text() == ""
    assert ui_window.ui.txt_pin_moi.text() == ""
    assert ui_window.ui.txt_pin_xacnhan.text() == ""
    assert ui_window.ui.btn_save_security.isEnabled() is True


def test_handle_change_pin_fails_due_to_business_contract_exceptions(mocker, ui_window, mock_security_service):
    """
    KỊCH BẢN 4: Đổi mã PIN thất bại do vi phạm luật bảo mật từ tầng Service đẩy lên (Ví dụ: Sai mã PIN cũ)
    """
    # GIVEN: Nhập liệu thông tin sai mã PIN cũ
    ui_window.ui.txt_pin_hientai.setText("9999")
    ui_window.ui.txt_pin_moi.setText("5678")
    ui_window.ui.txt_pin_xacnhan.setText("5678")

    # Cấu hình tầng dịch vụ ném ra lỗi ValueError nghiệp vụ cụ thể
    error_msg = "Mã PIN hiện tại không chính xác!"
    mock_security_service.change_pin.side_effect = ValueError(error_msg)

    # Đánh chặn Popup warning cản đường test
    mock_warning_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.warning")

    # WHEN: Tiến hành nhấn lệnh đổi mật mã
    ui_window.ui.btn_save_security.click()

    # THEN:
    # 1. Giao diện bắt được Exception nghiệp vụ và đẩy lên Popup cảnh báo
    mock_warning_box.assert_called_once_with(ui_window, "Lỗi bảo mật", error_msg)

    # 2. BẢO VỆ TIẾN TRÌNH: Các ô nhập liệu mật mã mới vẫn phải được giữ nguyên trạng thái cũ
    assert ui_window.ui.txt_pin_moi.text() == "5678"
    assert ui_window.ui.btn_save_security.isEnabled() is True