import pytest
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import QMessageBox

from app.modules.setting.dtos.backup_config_dto import BackupConfigDTO
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.ui.controllers.setting_management_controller import SettingManagementController


# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================

@pytest.fixture
def mock_store_config_service(mocker):
    """Làm giả dịch vụ thông tin cửa hàng để Window nạp thành công ở hàm load"""
    service = mocker.Mock()
    service.get_store_config.return_value = StoreConfigDTO(
        name="Văn phòng phẩm ABC",
        phone="0901 234 567",
        address="Hà Nội",
        paper_size="K80",
        footer="Cảm ơn quý khách!"
    )
    return service


@pytest.fixture
def mock_security_service(mocker):
    """Làm giả dịch vụ bảo mật mã PIN"""
    return mocker.Mock()


@pytest.fixture
def mock_backup_service(mocker):
    """Làm giả cổng nghiệp vụ BackupService để kiểm tra tương tác chỉ lệnh"""
    service = mocker.Mock()
    # Trả về một mốc cấu hình mặc định ban đầu dưới DB
    service.get_backup_config.return_value = BackupConfigDTO(
        auto_enabled=False,
        backup_time="22:00",
        folder_path="/Users/minhtoan/Documents/POS_Backup"
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
    qtbot.addWidget(window)  # Đăng ký với bot quản lý RAM giải phóng bộ nhớ
    window.load_current_settings()  # Triệu hồi lệnh đổ dữ liệu lên Form ban đầu

    window.show()

    return window


# ==============================================================================
# UI TEST CASES (Kiểm thử hành vi tương tác và trạng thái Form)
# ==============================================================================

def test_initial_ui_state_should_render_correctly_and_keep_save_button_disabled(ui_window):
    """
    KỊCH BẢN 1: Khởi động giao diện cấu hình thiết lập
    - Kỳ vọng: Dữ liệu từ DB đổ đúng lên các control, nút 'Lưu cấu hình' bắt buộc phải ẨN MỜ (Disabled).
    """
    assert ui_window.ui.chk_toggle.isChecked() is False
    assert ui_window.ui.txt_backup_path.text() == "/Users/minhtoan/Documents/POS_Backup"
    assert ui_window.ui.time_backup.time().toString("HH:mm") == "22:00"
    assert ui_window.ui.btn_save_backup_config.isEnabled() is False


def test_user_interaction_should_trigger_dirty_checking_and_enable_save_button(qtbot, ui_window):
    """
    KỊCH BẢN 2: Người dùng thay đổi thông số trên giao diện
    - Khi thay đổi checkbox tự động sao lưu -> Nút Lưu sáng lên.
    - Khi khôi phục checkbox về trạng thái cũ -> Nút Lưu ẩn mờ đi (Trở lại Baseline).
    """
    # GIVEN: Ban đầu nút lưu đang mờ
    assert ui_window.ui.btn_save_backup_config.isEnabled() is False

    ui_window.ui.chk_toggle.click()

    # THEN: Checkbox đã chuyển trạng thái thành True và kích hoạt Dirty Checking làm sáng nút Lưu
    assert ui_window.ui.chk_toggle.isChecked() is True
    assert ui_window.ui.btn_save_backup_config.isEnabled() is True

    # WHEN: Click một lần nữa để đảo ngược trạng thái về ban đầu (Baseline)
    ui_window.ui.chk_toggle.click()

    # THEN: Khớp dữ liệu gốc -> Nút lưu phải tự động ẨN MỜ đi
    assert ui_window.ui.chk_toggle.isChecked() is False
    assert ui_window.ui.btn_save_backup_config.isEnabled() is False

def test_browse_path_button_should_update_line_edit_and_brighten_save_button(mocker, qtbot, ui_window):
    """
    KỊCH BẢN 3: Người dùng bấm biểu tượng 📁 để chọn thư mục Drive/OneDrive mới
    """
    new_path = "/Users/minhtoan/GoogleDrive/New_Backup_Folder"
    mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QFileDialog.getExistingDirectory",
        return_value=new_path
    )

    # WHEN: Giả lập click nút mở thư mục
    qtbot.mouseClick(ui_window.ui.btn_browse_path, Qt.MouseButton.LeftButton)

    # THEN: Ô text đường dẫn phải ăn theo giá trị mới chọn và nút Lưu sáng lên nhờ Signal Cascade
    assert ui_window.ui.txt_backup_path.text() == new_path
    assert ui_window.ui.btn_save_backup_config.isEnabled() is True


def test_handle_save_backup_config_successfully_should_invoke_service_and_dim_save_button(mocker, qtbot, ui_window,
                                                                                          mock_backup_service):
    """
    KỊCH BẢN 4: Thực thi bấm nút "Lưu cấu hình" thành công
    """
    ui_window.ui.time_backup.setTime(QTime(23, 0))
    assert ui_window.ui.btn_save_backup_config.isEnabled() is True

    mock_msg_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.information")
    mock_backup_service.save_backup_config.return_value = True

    # WHEN: Thu ngân click nút [Lưu cấu hình]
    qtbot.mouseClick(ui_window.ui.btn_save_backup_config, Qt.MouseButton.LeftButton)

    # THEN:
    mock_backup_service.save_backup_config.assert_called_once()
    mock_msg_box.assert_called_once_with(ui_window, "Thành công", "Đã lưu cấu hình sao lưu dữ liệu tự động!")
    assert ui_window.ui.btn_save_backup_config.isEnabled() is False


def test_handle_manual_backup_success_should_show_info_popup(mocker, qtbot, ui_window, mock_backup_service):
    """
    KỊCH BẢN 5: Người dùng bấm nút "Sao lưu ngay" (Tác vụ thủ công) thành công
    """
    # GIVEN: Cấu hình mock trích xuất trả về đường dẫn file vật lý thành công
    mock_backup_service.execute_backup.return_value = "/Backup_Path/pos_backup_2026.sql"
    mock_msg_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.information")

    # WHEN: Bấm nút hành động
    qtbot.mouseClick(ui_window.ui.btn_manual_backup, Qt.MouseButton.LeftButton)

    # THEN:
    mock_backup_service.execute_backup.assert_called_once()

    mock_msg_box.assert_called_once_with(
        ui_window, "Sao lưu thành công",
        "Hệ thống đã xuất dữ liệu an toàn thành công!\nTập tin: /Backup_Path/pos_backup_2026.sql"
    )


def test_handle_restore_backup_cancelled_by_user_should_do_nothing(mocker, qtbot, ui_window, mock_backup_service):
    """
    KỊCH BẢN 6: Thu ngân bấm "Khôi phục" nhưng chọn "NO" ở hộp thoại xác nhận nguy hiểm
    """
    mock_warning_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.No
    )
    mock_file_dialog = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QFileDialog.getOpenFileName")

    # WHEN: Bấm nút khôi phục dữ liệu
    qtbot.mouseClick(ui_window.ui.btn_restore_backup, Qt.MouseButton.LeftButton)

    # THEN:
    mock_warning_box.assert_called_once()
    mock_file_dialog.assert_not_called()
    mock_backup_service.execute_restore.assert_not_called()


def test_handle_restore_backup_confirmed_should_execute_full_restore(mocker, qtbot, ui_window, mock_backup_service):
    """
    KỊCH BẢN 7: Thu ngân xác nhận "YES" ghi đè dữ liệu và lựa chọn tệp tin .sql hợp lệ
    """
    mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes
    )
    mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QFileDialog.getOpenFileName",
        return_value=("/Saved_Path/old_data.sql", "Database Files (*.sql)")
    )
    mock_backup_service.execute_restore.return_value = True
    mock_info_box = mocker.patch(
        "app.modules.setting.ui.controllers.setting_management_controller.QMessageBox.information")

    # WHEN: Kích hoạt nút bấm
    qtbot.mouseClick(ui_window.ui.btn_restore_backup, Qt.MouseButton.LeftButton)

    # THEN: Khép kín luồng xử lý tương tác nạp đè dữ liệu
    mock_backup_service.execute_restore.assert_called_once_with("/Saved_Path/old_data.sql")

    mock_info_box.assert_called_once_with(
        ui_window, "Phục hồi thành công",
        "Cơ sở dữ liệu đã phục hồi trạng thái nguyên vẹn!"
    )