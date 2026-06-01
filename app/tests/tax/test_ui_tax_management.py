import pytest
from decimal import Decimal
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QHeaderView, QAbstractItemView

from app.modules.tax.ui.controllers.tax_management_controller import TaxManagementController
from app.modules.tax.dtos.tax_dto import TaxLedgerDTO, TaxLedgerDetailDTO, YearlyTaxReportDTO, MonthlyTaxDetailDTO



class FakeTaxServiceForUI:
    def __init__(self):
        self.mock_limits = (Decimal('3000000000'), Decimal('50000000000'))
        self.draft_config = None
        self.staged_called = False
        self.closed_called = False

        # Chuẩn bị sẵn mảng dữ liệu Master mẫu cho Tab 2
        self.ledgers = [
            TaxLedgerDTO(
                id=1, apply_year=2026, total_revenue=Decimal('2000000000'), total_cost=Decimal('0'),
                final_vat_amount=Decimal('20000000'), final_pit_amount=Decimal('5000000'),
                pit_method='FLAT_RATE', status='DRAFT', threshold_amount=Decimal('1000000000'),
                vat_percent=Decimal('1.0'), pit_percent=Decimal('0.5'), finalized_at=None
            )
        ]

    def get_tax_scale_limits(self):
        return self.mock_limits

    def get_active_draft_ledger_config(self, year: int):
        return self.draft_config

    def generate_yearly_tax_report_live(self, year, threshold, vat_percent, pit_percent, pit_method):
        monthly_details = [
            MonthlyTaxDetailDTO(m, Decimal('100000000'), Decimal('1000000'), Decimal('500000'), Decimal('1500000')) for
            m in range(1, 13)]
        return YearlyTaxReportDTO(year, Decimal('1200000000'), True, Decimal('18000000'), monthly_details)

    def stage_temporary_ledger(self, year, threshold, vat_percent, pit_percent, pit_method):
        self.staged_called = True
        return True

    def get_all_ledgers(self):
        return self.ledgers

    def get_ledger_details(self, ledger_id: int):
        return [TaxLedgerDetailDTO(i, ledger_id, i, Decimal('100000000'), Decimal('0'), Decimal('1000000'),
                                   Decimal('500000')) for i in range(1, 13)]

    def close_and_freeze_ledger(self, year: int):
        self.closed_called = True
        return True


class FakeSettingServiceForUI:
    def __init__(self):
        self.pin_valid = True

    def verify_app_pin(self, pin: str) -> bool:
        return self.pin_valid


# =====================================================================================
# FIXTURES KHỞI TẠO CỬA SỔ WIDGET ĐỒ HỌA
# =====================================================================================

@pytest.fixture
def tax_ui_window(qtbot):
    """Khởi tạo cửa sổ đồ họa thật, liên kết Fake Services và đăng ký vòng đời với qtbot"""
    fake_tax_service = FakeTaxServiceForUI()
    fake_setting_service = FakeSettingServiceForUI()

    window = TaxManagementController(fake_tax_service, fake_setting_service)
    qtbot.addWidget(window)

    window.fake_tax_service = fake_tax_service
    window.fake_setting_service = fake_setting_service
    return window


# =====================================================================================
# CÁC KỊCH BẢN KIỂM THỬ UI
# =====================================================================================

def test_ui_precondition_close_ledger_aborts_if_user_enters_incorrect_security_pin(qtbot, tax_ui_window, mocker):
    """
    TC_UI_Pre_01: Chặn đứng luồng chốt sổ khi nhập sai mã PIN.
    KỲ VỌNG UI HỘP ĐEN: Nhập sai mã PIN, giao diện phải hiện popup báo lỗi và TUYỆT ĐỐI không gọi xuống tầng Service.
    """
    window = tax_ui_window
    window.fake_setting_service.pin_valid = False  # Ép nhập sai mã PIN

    # 1. Arrange: Chuyển sang Tab 2 và nạp dữ liệu mồi chuẩn chỉ từ hàm nạp hệ thống
    window.ui.tabWidget_tax.setCurrentIndex(1)
    window.load_history_master_table()

    # Giả lập hành vi người dùng click chọn dòng đầu tiên của bảng Master thông qua việc kích hoạt Signal
    window.ui.tbl_tax_history_master.selectRow(0)
    window.handle_master_row_selected()  # Gọi đúng hàm xử lý của Controller, không gọi qua đối tượng UI thô

    # Patch tóm sống các hộp thoại hệ thống
    mocker.patch('PyQt6.QtWidgets.QMessageBox.warning', return_value=QMessageBox.StandardButton.Yes)
    mocker.patch('PyQt6.QtWidgets.QInputDialog.getText', return_value=("WRONG_PIN", True))
    mocker.patch('PyQt6.QtWidgets.QMessageBox.warning')

    # WHEN: Người dùng click chuột vào nút "🔒 CHỐT SỔ & KHÓA KỲ THUẾ NĂM"
    qtbot.mouseClick(window.ui.btn_close_ledger, Qt.MouseButton.LeftButton)

    # THEN: Lệnh gọi đóng băng xuống backend bắt buộc phải đứng im
    assert window.fake_tax_service.closed_called is False, "LỖI UI: Hệ thống vẫn gọi dịch vụ khóa sổ dù người dùng nhập sai mã PIN."


def test_ui_postcondition_live_recalculation_updates_formulas_and_progress_bar_on_spinbox_change(qtbot, tax_ui_window):
    """
    TC_UI_Post_01: Phản ứng live của nhãn công thức và thanh tiến độ đồ họa.
    """
    window = tax_ui_window

    # WHEN: Thay đổi giá trị Thuế suất GTGT lên thành 5.5%
    window.ui.spn_vat_rate.setValue(5.5)

    # THEN: Nhãn chữ công thức bổ sung dưới SpinBox phải tự động đổi text
    assert "5.5%" in window.ui.lbl_vat_formula.text(), "LỖI UI: Nhãn công thức live không tự động cập nhật số liệu theo SpinBox."
    assert window.ui.bar_threshold.value() > 0 or "Vùng an toàn" in window.ui.bar_threshold.format()


def test_ui_postcondition_master_detail_click_fills_frozen_headers_on_tab_2(qtbot, tax_ui_window):
    """
    TC_UI_Post_02: Đồng bộ thông tin Header đóng băng tại lưới xem chi tiết.
    """
    window = tax_ui_window
    window.ui.tabWidget_tax.setCurrentIndex(1)

    # Nạp dữ liệu mồi vào bảng Master trái
    window.load_history_master_table()

    # Người dùng chọn dòng Master đầu tiên và kích hoạt đồng bộ
    window.ui.tbl_tax_history_master.selectRow(0)
    window.handle_master_row_selected()

    # THEN: Bộ 4 nhãn thông tin cấu hình Header đóng băng bắt buộc phải được đổ đầy dữ liệu
    assert "--" not in window.ui.lbl_md_threshold.text(), "LỖI UI: Chưa điền thông số Ngưỡng miễn thuế đóng băng lên Header Detail."
    assert "Khoán % doanh thu" in window.ui.lbl_md_method.text()
    assert "1.0%" in window.ui.lbl_md_vat_rate.text()

    # Kiểm tra tính chất căn lề dãn đều (Đã nhận diện lớp QHeaderView hợp lệ)
    assert window.ui.tbl_ledger_details.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Stretch


def test_ui_invariant_splitter_and_tables_must_keep_edit_locks_at_all_times(tax_ui_window):
    """
    TC_UI_Inv_01: Bất biến an toàn dữ liệu hiển thị (UI Read-Only Lock Invariant).
    """
    window = tax_ui_window

    # Khẳng định 3 bảng luôn luôn khóa tính năng sửa ô trực tiếp để bảo vệ dữ liệu kế toán
    assert window.ui.tbl_monthly_tax.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert window.ui.tbl_ledger_details.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert window.ui.tbl_tax_history_master.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers