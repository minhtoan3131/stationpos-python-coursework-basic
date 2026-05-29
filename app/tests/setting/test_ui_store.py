import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.ui.controllers.setting_management_controller import SettingManagementController


# ==============================================================================
# PYTEST FIXTURES (Cô lập hoàn toàn các dịch vụ hạ tầng bằng Mock)
# ==============================================================================

@pytest.fixture
def mock_store_config_service(mocker):
    """Làm giả dịch vụ thông tin cửa hàng để Window nạp dữ liệu gốc"""
    service = mocker.Mock()
    service.get_store_config.return_value = StoreConfigDTO(
        name="Văn phòng phẩm ABC",
        phone="0901234567",
        address="123 Đường Láng, Hà Nội",
        paper_size="K80",
        footer="Cảm ơn quý khách, hẹn gặp lại!"
    )
    return service


@pytest.fixture
def mock_security_service(mocker):
    """Làm giả dịch vụ bảo mật mã PIN"""
    return mocker.Mock()


@pytest.fixture
def mock_backup_service(mocker):
    """Làm giả dịch vụ sao lưu dữ liệu"""
    service = mocker.Mock()
    service.get_backup_config.return_value = BackupConfigDTO(
        auto_enabled=False,
        backup_time="22:00",
        folder_path="/Users/test/Backup"
    )
    return service


@pytest.fixture
def ui_window(qtbot, mock_store_config_service, mock_security_service, mock_backup_service):
    """Khởi tạo Controller Giao diện, đăng ký vòng đời với qtbot và nạp data gốc"""
    window = SettingManagementController(
        store_config_service=mock_store_config_service,
        security_service=mock_security_service,
        backup_service=mock_backup_service
    )
    qtbot.addWidget(window)
    window.load_current_settings()
    window.show()
    return window


# ==============================================================================
# UI TEST CASES (Kiểm thử hành vi an toàn trên mọi hệ điều hành)
# ==============================================================================

def test_initial_store_ui_state_should_render_correctly_and_keep_save_button_disabled(ui_window):
    """
    KỊCH BẢN 1: Mở phân hệ Giao diện cấu hình thiết lập shop
     Đồng bộ hóa đúng chuỗi hiển thị thực tế của ComboBox K80
    """
    assert ui_window.ui.txt_ten.text() == "Văn phòng phẩm ABC"
    assert ui_window.ui.txt_sdt.text() == "0901234567"
    assert ui_window.ui.txt_diachi.text() == "123 Đường Láng, Hà Nội"
    assert ui_window.ui.txt_loichao.text() == "Cảm ơn quý khách, hẹn gặp lại!"

    # SỬA LỖI 1: Khớp chuỗi chi tiết hiển thị trên UI thật
    assert ui_window.ui.cb_giay.currentText() == "K80 — khổ lớn 80mm"

    # Nút lưu mặc định ẩn mờ chuẩn chỉ
    assert ui_window.ui.btn_save_bill.isEnabled() is False


def test_store_text_modification_should_trigger_dirty_checking_and_enable_save_button(ui_window):
    """
    KỊCH BẢN 2: Chủ quán dùng bàn phím chỉnh sửa thông tin trên Form
     Sử dụng .setText() để kích hoạt textChanged an toàn, loại bỏ triệt để crash SIGABRT trên Mac
    """
    assert ui_window.ui.btn_save_bill.isEnabled() is False

    # WHEN: Thay đổi text trực tiếp bằng lệnh Qt (Vẫn phát tín hiệu textChanged y hệt người dùng gõ thật)
    ui_window.ui.txt_ten.setText("Văn phòng phẩm ABC Mới")

    # THEN: Kích hoạt Dirty Checking làm sáng nút Lưu lên
    assert ui_window.ui.btn_save_bill.isEnabled() is True

    # WHEN: Trả text về nguyên bản ban đầu giống mốc Database
    ui_window.ui.txt_ten.setText("Văn phòng phẩm ABC")

    # THEN: Dữ liệu sạch sẽ trùng khớp mốc DB ban đầu -> Nút lưu tự động ẨN MỜ đi
    assert ui_window.ui.btn_save_bill.isEnabled() is False


def test_combobox_paper_size_change_should_trigger_dirty_checking(ui_window):
    """
    KỊCH BẢN 3: Thay đổi kích thước khổ giấy in hóa đơn trên Dropdown QComboBox
    """
    assert ui_window.ui.btn_save_bill.isEnabled() is False

    # WHEN: Thay đổi index combobox sang 1 (Khổ giấy K58)
    ui_window.ui.cb_giay.setCurrentIndex(1)

    # THEN: Nút lưu phải sáng rõ
    assert ui_window.ui.btn_save_bill.isEnabled() is True

    # WHEN: Chọn ngược về index 0 (Khổ K80 ban đầu)
    ui_window.ui.cb_giay.setCurrentIndex(0)

    # THEN: Nút lưu phải mờ đi lập tức
    assert ui_window.ui.btn_save_bill.isEnabled() is False


def test_handle_save_bill_info_successfully_should_invoke_service_and_reset_baseline(mocker, qtbot, ui_window,
                                                                                     mock_store_config_service):
    """
    KỊCH BẢN 4: Người dùng thực hiện bấm nút "Lưu thông tin" hóa đơn thành công
    """
    # GIVEN: Làm bẩn dữ liệu bằng cách đặt số điện thoại mới
    ui_window.ui.txt_sdt.setText("0999999999")
    assert ui_window.ui.btn_save_bill.isEnabled() is True

    mock_info_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.information")
    mock_store_config_service.save_store_config.return_value = True

    # WHEN: Người dùng nhấn nút [Lưu thông tin]
    qtbot.mouseClick(ui_window.ui.btn_save_bill, Qt.MouseButton.LeftButton)

    # THEN:
    mock_store_config_service.save_store_config.assert_called_once()
    called_dto = mock_store_config_service.save_store_config.call_args[0][0]
    assert called_dto.phone == "0999999999"

    mock_info_box.assert_called_once_with(ui_window, "Thành công", "Đã cập nhật thông tin cửa hàng thành công!")
    assert ui_window.ui.btn_save_bill.isEnabled() is False


def test_handle_save_bill_info_fails_validation_when_name_is_empty(mocker, qtbot, ui_window, mock_store_config_service):
    """
    KỊCH BẢN 5: Người dùng cố tình xóa sạch tên cửa hàng và bấm nút Lưu
    """
    # GIVEN: Xóa trống ô tên cửa hàng
    ui_window.ui.txt_ten.clear()
    assert ui_window.ui.btn_save_bill.isEnabled() is True

    mock_warning_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.warning")

    # WHEN: Thu ngân bấm nút [Lưu thông tin] khi tên đang rỗng
    qtbot.mouseClick(ui_window.ui.btn_save_bill, Qt.MouseButton.LeftButton)

    # THEN:
    mock_warning_box.assert_called_once_with(ui_window, "Lỗi dữ liệu", "Tên cửa hàng không được để trống!")
    mock_store_config_service.save_store_config.assert_not_called()
    assert ui_window.ui.btn_save_bill.isEnabled() is True