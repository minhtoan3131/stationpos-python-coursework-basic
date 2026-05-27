import pytest
from datetime import datetime
from decimal import Decimal
from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QDialog
from PyQt6.QtCore import Qt

from app.core.exceptions.validation_exception import ValidationException
from app.modules.sale.ui.controllers.invoice_history_controller import InvoiceHistoryController
from app.modules.sale.ui.generated.ui_sales_management import Ui_SalesManagementWidget


# ==========================================
# 1. SETUP FIXTURE CHO TẦNG UI HISTORY TEST
# ==========================================
@pytest.fixture
def mock_invoice_history_service(mocker):
    """Làm giả hoàn toàn tầng Service để cách ly UI khỏi Database thực tế"""
    return mocker.Mock()


@pytest.fixture
def history_ui(qtbot, mock_invoice_history_service):
    """Khởi tạo Widget cha, nạp giao diện mẫu và liên kết bộ điều phối Controller"""
    widget = QWidget()
    ui = Ui_SalesManagementWidget()
    ui.setupUi(widget)

    # Ép hiển thị Widget lên màn hình để PyQt khởi tạo đầy đủ sub-widgets dòng tiền
    widget.show()
    qtbot.addWidget(widget)

    # Chuyển sang Tab số 1: Nhật ký hóa đơn
    ui.tabWidget_sales.setCurrentIndex(1)

    controller = InvoiceHistoryController(ui, mock_invoice_history_service)
    return controller, ui, mock_invoice_history_service, widget


# ==========================================
# 2. TEST UC1: TẢI DANH SÁCH MASTER VÀ THIẾT LẬP MÀU SẮC
# ==========================================
def test_uc1_load_master_data_updates_table_and_formats_status_colors(history_ui):
    """Kiểm chứng UC1: Đổ dữ liệu lên bảng trái phải phân cấp màu sắc chuẩn và clear bảng phải"""
    controller, ui, mock_service, _ = history_ui

    # GIVEN: Giả lập Service trả về 2 hóa đơn (1 Hoàn thành, 1 Đã hủy)
    mock_service.search_invoices.return_value = [
        {
            'code': 'HD-001', 'created_at': datetime(2026, 5, 27, 10, 0),
            'final_amount': Decimal('150000'), 'payment_method': 'CASH', 'status': 'COMPLETED'
        },
        {
            'code': 'HD-002', 'created_at': datetime(2026, 5, 27, 10, 5),
            'final_amount': Decimal('210000'), 'payment_method': 'TRANSFER', 'status': 'CANCELLED',
            'cancel_reason': 'Khách trả hàng'
        }
    ]

    # Mồi dữ liệu rác vào bảng Detail để check xem hệ thống có tự dọn dẹp không
    ui.tbl_invoice_details.setRowCount(3)
    ui.lbl_md_invoice_id.setText("Mã cũ")

    # WHEN: Gọi hàm tải dữ liệu (Tương đương kích hoạt sự kiện nút Lọc/Tìm kiếm)
    controller.load_master_data()

    # THEN: Khẳng định hệ quả trạng thái UI để lại
    assert ui.tbl_invoice_master.rowCount() == 2
    assert ui.tbl_invoice_master.item(0, 0).text() == "HD-001"
    assert ui.tbl_invoice_master.item(1, 0).text() == "HD-002"

    # Dòng 0 (COMPLETED) -> Chữ "Hoàn thành" màu xanh lá
    assert ui.tbl_invoice_master.item(0, 4).text() == "Hoàn thành"
    assert ui.tbl_invoice_master.item(0, 4).foreground().color() == Qt.GlobalColor.darkGreen

    # Dòng 1 (CANCELLED) -> Chữ "Đã hủy" màu đỏ và bôi đậm
    assert ui.tbl_invoice_master.item(1, 4).text() == "Đã hủy"
    assert ui.tbl_invoice_master.item(1, 4).foreground().color() == Qt.GlobalColor.red
    assert ui.tbl_invoice_master.item(1, 4).font().bold() is True

    # Khung chi tiết bên phải phải bị xóa trắng hoàn toàn để tránh râu ông nọ cắm cằm bà kia
    assert ui.tbl_invoice_details.rowCount() == 0
    assert "0 VND" in ui.lbl_detail_total_value.text()


# ==========================================
# 3. TEST UC2: XEM CHI TIẾT HÓA ĐƠN HOÀN THÀNH (BẬT NÚT HỦY)
# ==========================================
def test_uc2_select_completed_invoice_loads_details_and_enables_cancel_btn(history_ui):
    """Kiểm chứng UC2: Click chọn hóa đơn COMPLETED -> Hiện đầy đủ chi tiết và BẬT nút Hủy"""
    controller, ui, mock_service, _ = history_ui

    # GIVEN: Gán dữ liệu cache Master và tạo hàng chọn trên bảng
    ui.tbl_invoice_master.setRowCount(1)
    ui.tbl_invoice_master.setItem(0, 0, QTableWidgetItem("HD-001"))

    # Cấu hình cục dữ liệu chi tiết thật từ Service trả về
    mock_service.get_invoice_full_details.return_value = {
        "metadata": {
            'code': 'HD-001', 'created_at': datetime(2026, 5, 27, 10, 0),
            'final_amount': Decimal('150000'), 'payment_method': 'CASH',
            'cash_received': Decimal('200000'), 'status': 'COMPLETED'
        },
        "items": [
            {'product_name': 'Bút bi Thiên Long', 'unit_name': 'Cái', 'quantity': 5, 'unit_price': Decimal('10000'),
             'total_price': Decimal('50000')}
        ]
    }

    # WHEN: Giả lập thu ngân click chọn dòng số 0 trên bảng Master
    ui.tbl_invoice_master.setCurrentCell(0, 0)

    # THEN: Cập nhật Panel Metadata bên phải chính xác
    assert "HD-001" in ui.lbl_md_invoice_id.text()
    assert "Hoàn thành" in ui.lbl_md_invoice_status.text()
    assert "150,000" in ui.lbl_detail_total_value.text()
    assert ui.tbl_invoice_details.rowCount() == 1
    assert ui.tbl_invoice_details.item(0, 0).text() == "Bút bi Thiên Long"

    # Nút Hủy hóa đơn bắt buộc phải MỞ (Enabled = True) để kế toán thao tác
    assert ui.btn_cancel_invoice.isEnabled() is True


# ==========================================
# 4. TEST UC3: XEM CHI TIẾT HÓA ĐƠN ĐÃ HỦY (TẮT NÚT HỦY)
# ==========================================
def test_uc3_select_cancelled_invoice_shows_reason_and_disables_cancel_btn(history_ui):
    """Kiểm chứng UC3: Click chọn hóa đơn CANCELLED -> Hiện lý do hủy và KHÓA nút Hủy"""
    controller, ui, mock_service, _ = history_ui

    ui.tbl_invoice_master.setRowCount(1)
    ui.tbl_invoice_master.setItem(0, 0, QTableWidgetItem("HD-002"))

    mock_service.get_invoice_full_details.return_value = {
        "metadata": {
            'code': 'HD-002', 'created_at': datetime(2026, 5, 27, 10, 5),
            'final_amount': Decimal('210000'), 'payment_method': 'TRANSFER',
            'cash_received': Decimal('210000'), 'status': 'CANCELLED', 'cancel_reason': 'Khách đổi ý'
        },
        "items": []
    }

    # WHEN: Thu ngân click chọn dòng hóa đơn đã hủy
    ui.tbl_invoice_master.setCurrentCell(0, 0)

    # THEN: Giao diện hiển thị lý do hủy trực quan
    assert "Đã hủy" in ui.lbl_md_invoice_status.text()
    assert "Khách đổi ý" in ui.lbl_md_invoice_status.text()

    # Nút Hủy hóa đơn bắt buộc phải KHÓA (Enabled = False) chống hành vi hủy lặp lại
    assert ui.btn_cancel_invoice.isEnabled() is False


# ==========================================
# 5. TEST UC4: XUẤT EXCEL (HAPPY PATH & EDGE CASES)
# ==========================================
def test_uc4_export_excel_success_workflow(history_ui, mocker):
    """Kiểm chứng UC4: Bấm xuất -> Chọn folder -> Exporter chạy thành công -> Hiện popup info"""
    controller, ui, mock_service, _ = history_ui

    controller.selected_invoice = "HD-001"
    mock_service.export_invoice_to_excel.return_value = {"metadata": {}, "items": []}

     Đổi từ inventory_history_controller sang invoice_history_controller
    mock_file_dialog = mocker.patch(
        "app.modules.sale.ui.controllers.invoice_history_controller.QFileDialog.getSaveFileName"
    )
    mock_file_dialog.return_value = ("/tmp/HoaDon_HD-001.xlsx", "Excel Files (*.xlsx)")

     Đổi từ inventory_history_controller sang invoice_history_controller (cho QMessageBox)
    mocker.patch("app.modules.sale.utils.invoice_history_excel_exporter.InvoiceHistoryExcelExporter.export_detail", return_value=True)
    mock_info_box = mocker.patch(
        "app.modules.sale.ui.controllers.invoice_history_controller.QMessageBox.information"
    )

    controller.handle_export_excel()

    mock_service.export_invoice_to_excel.assert_called_once_with("HD-001")
    mock_info_box.assert_called_once()


def test_uc4_export_excel_aborted_by_user_at_file_dialog(history_ui, mocker):
    """Kiểm chứng UC4: Bấm xuất -> Người dùng ấn Cancel ở hộp thoại -> Dừng luồng, không chạy Exporter"""
    controller, ui, mock_service, _ = history_ui
    controller.selected_invoice = "HD-001"

     Đổi target sang invoice_history_controller
    mocker.patch(
        "app.modules.sale.ui.controllers.invoice_history_controller.QFileDialog.getSaveFileName",
        return_value=("", "")
    )
    mock_exporter = mocker.patch("app.modules.sale.utils.invoice_history_excel_exporter.InvoiceHistoryExcelExporter.export_detail")

    controller.handle_export_excel()

    mock_exporter.assert_not_called()


def test_ui_cancel_invoice_action_shows_warning_popup_on_validation_exception(history_ui, mocker):
    """
    TC_UI_01: Đánh chặn vi phạm nghiệp vụ (Cố tình hủy hóa đơn sai lệch).
    Kiểm chứng: Khi Service ném ValidationException, UI phải hiển thị QMessageBox.warning cảnh báo thân thiện.
    """
    controller, ui, mock_service, _ = history_ui
    controller.selected_invoice = "HD-001"

    # Giả lập kế toán nhập lý do hủy hóa đơn và nhấn OK
    mocker.patch(
        "app.modules.sale.ui.controllers.invoice_history_controller.QInputDialog.getText",
        return_value=("Khách trả lại hàng", True)
    )

    # Kích hoạt lỗi Validation từ Service đưa lên
    mock_service.execute_cancel_invoice.side_effect = ValidationException("Vui lòng cung cấp lý do hủy hóa đơn.")

    # Khống chế QMessageBox để tránh hiện UI thật khi chạy test tự động
    mock_warning_box = mocker.patch(
        "app.modules.sale.ui.controllers.invoice_history_controller.QMessageBox.warning"
    )

    # === ĐÃ SỬA: Gọi đúng tên hàm điều phối trong mã nguồn của bạn ===
    controller.handle_cancel_invoice()

    # KIỂM CHỨNG HẬU ĐIỀU KIỆN
    mock_service.execute_cancel_invoice.assert_called_once_with("HD-001", "Khách trả lại hàng")
    mock_warning_box.assert_called_once_with(None, "Chặn nghiệp vụ", "Vui lòng cung cấp lý do hủy hóa đơn.")