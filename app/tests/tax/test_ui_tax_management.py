import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from app.modules.tax.ui.controllers.tax_management_controller import TaxManagementController
from app.modules.tax.services.tax_service import ITaxService
from app.modules.tax.dtos.tax_dto import TaxConfigDTO, YearlyTaxReportDTO, MonthlyTaxDetailDTO


# ==========================================
# THIẾT LẬP MÔI TRƯỜNG & GIẢ LẬP BIÊN GIỚI
# ==========================================

@pytest.fixture
def sample_tax_config():
    """Tạo cấu hình thuế mẫu (Ngưỡng 100tr, VAT 1%, PIT 0.5%)"""
    return TaxConfigDTO(
        apply_year=2026,
        threshold_amount=Decimal('100000000'),
        vat_percent=Decimal('1.0'),
        pit_percent=Decimal('0.5')
    )


@pytest.fixture
def sample_report_over_threshold():
    """Tạo báo cáo mẫu cho kịch bản ĐÃ VƯỢT NGƯỠNG (Happy Path có đóng thuế)"""
    monthly_details = []
    # Giả lập tháng 1 bán được 120tr, phải nộp 1.8tr tiền thuế
    monthly_details.append(MonthlyTaxDetailDTO(
        month=1, revenue=Decimal('120000000'),
        vat_amount=Decimal('1200000'), pit_amount=Decimal('600000'), total_tax=Decimal('1800000')
    ))
    # Fill 11 tháng còn lại bằng 0 cho đủ bảng
    for i in range(2, 13):
        monthly_details.append(MonthlyTaxDetailDTO(i, Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')))

    return YearlyTaxReportDTO(
        year=2026,
        total_revenue=Decimal('120000000'),
        is_over_threshold=True,
        total_tax_amount=Decimal('1800000'),
        monthly_details=monthly_details
    )


@pytest.fixture
def tax_window(qtbot, mocker, sample_tax_config, sample_report_over_threshold):
    """Khởi tạo Controller, gắn Mock Service và đăng ký vòng đời với qtbot"""
    mock_service = mocker.Mock(spec=ITaxService)

    # Setup hành vi mặc định khi cửa sổ mở lên
    mock_service.get_or_create_config.return_value = sample_tax_config
    mock_service.generate_yearly_tax_report.return_value = sample_report_over_threshold
    mock_service.save_config.return_value = True

    # Cố định năm hiện tại là 2026 để test cảnh báo năm quá khứ ổn định
    mocker.patch('app.modules.tax.ui.controllers.tax_management_controller.datetime').now.return_value.year = 2026

    window = TaxManagementController(tax_service=mock_service)
    qtbot.addWidget(window)

    window.mock_service = mock_service
    return window


# ==========================================
# KIỂM THỬ NHÓM CHẶN LỖI UI (PRE-CONDITIONS)
# ==========================================

def test_should_show_warning_and_abort_save_when_editing_past_year_and_user_cancels(qtbot, tax_window, mocker):
    """TC_UI_Pre_01: Cảnh báo khi sửa dữ liệu năm cũ. Nếu User chọn 'No', tuyệt đối không gọi Backend lưu dữ liệu"""
    window = tax_window
    window.mock_service.reset_mock()

    # GIVEN: Người dùng chọn một năm trong quá khứ (Ví dụ: 2024 < 2026)
    window.ui.cbo_year.setCurrentText("2024")

    # Patch hộp thoại cảnh báo, ép nó tự động trả về nút "No" (Giả lập user quay xe)
    mock_warning = mocker.patch(
        'app.modules.tax.ui.controllers.tax_management_controller.QMessageBox.warning',
        return_value=QMessageBox.StandardButton.No
    )

    # WHEN: Người dùng bấm "Cập nhật & Tính toán"
    qtbot.mouseClick(window.ui.btn_apply_config, Qt.MouseButton.LeftButton)

    # THEN: 1. Hộp thoại cảnh báo rủi ro lịch sử phải được bật lên
    mock_warning.assert_called_once()
    assert "cảnh báo thay đổi dữ liệu lịch sử" in mock_warning.call_args[0][1].lower()

    # THEN: 2. Luồng xử lý phải dừng lại ngay, KHÔNG ĐƯỢC PHÉP gọi hàm save_config
    window.mock_service.save_config.assert_not_called()


# ==========================================
# KIỂM THỬ ĐỔ DỮ LIỆU THÀNH CÔNG (POST-CONDITIONS)
# ==========================================

def test_should_trigger_data_reload_when_combobox_year_is_changed(tax_window):
    """TC_UI_Post_01: Khi đổi năm trên ComboBox, UI phải tự động gọi Service lấy báo cáo năm mới"""
    window = tax_window
    window.mock_service.reset_mock()

    # WHEN: Đổi từ 2026 sang 2025
    window.ui.cbo_year.setCurrentText("2025")

    # THEN: Backend phải được gọi ngay lập tức với tham số year = 2025
    window.mock_service.get_or_create_config.assert_called_once_with(2025)
    window.mock_service.generate_yearly_tax_report.assert_called_once_with(2025)


def test_should_render_over_threshold_status_and_tax_table_correctly(qtbot, tax_window, sample_report_over_threshold):
    """TC_UI_Post_02: Trạng thái Vượt Ngưỡng phải bôi đỏ, hiển thị đúng tiền, format bảng căn phải chuẩn chỉ"""
    window = tax_window

    # Khi khởi tạo ở Fixture, dữ liệu Over Threshold đã được nạp

    # THEN: 1. Input Box cấu hình đổ đúng số
    assert window.ui.spn_threshold.value() == 100000000.0
    assert window.ui.spn_vat_rate.value() == 1.0

    # THEN: 2. Thẻ KPI
    assert window.ui.val_total_revenue.text() == "120,000,000 VND"
    assert window.ui.val_total_tax.text() == "1,800,000 VND"

    # THEN: 3. Đánh giá trạng thái (Phải bôi Đỏ)
    assert window.ui.val_tax_status.text() == "ĐÃ VƯỢT NGƯỠNG"
    assert "#ef4444" in window.ui.val_tax_status.styleSheet()  # Mã màu đỏ của Tailwind

    # THEN: 4. Kiểm chứng Bảng Chi tiết từng tháng (12 dòng)
    table = window.ui.tbl_monthly_tax
    assert table.rowCount() == 12

    # Dòng Tháng 1 (Có đóng thuế)
    assert table.item(0, 0).text() == "Tháng 1"

    # Kiểm chứng format tiền tệ và căn lề phải (Do TaxUIHelper xử lý)
    item_tax = table.item(0, 4)  # Cột tổng thuế
    assert item_tax.text() == "1,800,000"
    assert item_tax.textAlignment() == (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


# ==========================================
# KIỂM THỬ TÍNH BẤT BIẾN & KHÁNG SẬP (UI INVARIANTS)
# ==========================================

def test_should_catch_exception_and_show_critical_error_when_backend_fails_to_save(qtbot, tax_window, mocker):
    """TC_UI_Inv_01: Bấm lưu nhưng DB bị sập, UI phải chặn Crash và chìa thông báo lỗi đỏ"""
    window = tax_window

    # GIVEN: Cố tình đặt bẫy ném lỗi ở tầng Service
    window.mock_service.save_config.side_effect = Exception("Database Locked!")

    # Tóm sống hộp thoại lỗi Critical
    mock_critical = mocker.patch('app.modules.tax.ui.controllers.tax_management_controller.QMessageBox.critical')

    # WHEN: Bấm Cập nhật
    qtbot.mouseClick(window.ui.btn_apply_config, Qt.MouseButton.LeftButton)

    # THEN: App không sập (nếu sập test đã bị văng)
    # Hộp thoại lỗi phải hiện lên kèm theo thông báo kỹ thuật "Database Locked"
    mock_critical.assert_called_once()
    assert "Database Locked!" in mock_critical.call_args[0][2]