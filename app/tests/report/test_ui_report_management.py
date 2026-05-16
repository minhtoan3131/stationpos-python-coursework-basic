import pytest
from decimal import Decimal
from PyQt6.QtCore import Qt, QDate

from app.modules.report.ui.controllers.report_management_controller import ReportManagementController
from app.modules.report.services.report_service import ReportService
from app.modules.report.dtos.report_dto import (
    DashboardReportDTO, KPIDTO, RevenueTrendItemDTO,
    TopProductDTO, TransactionHistoryDTO, InventoryReportDTO
)


# ==========================================
# THIẾT LẬP MÔI TRƯỜNG & GIẢ LẬP BIÊN GIỚI
# ==========================================

@pytest.fixture
def sample_dashboard_dto():
    """Tạo gói dữ liệu DTO mẫu toàn vẹn phục vụ hiển thị (Happy Path)"""
    kpis = KPIDTO(
        total_orders=3,
        total_revenue=Decimal('500000'),
        total_profit=Decimal('210000'),
        total_stock_value=Decimal('1100000')
    )
    revenue_trend = [
        RevenueTrendItemDTO(date="15/05", revenue=Decimal('350000')),
        RevenueTrendItemDTO(date="16/05", revenue=Decimal('150000'))
    ]
    top_products = [
        TopProductDTO(product_name="Bút bi Thiên Long", quantity=100),
        TopProductDTO(product_name="Vở kẻ ngang", quantity=85)
    ]
    transactions = [
        TransactionHistoryDTO(invoice_code="HD003", created_at="2026-05-16 10:00", final_amount=Decimal('150000'),
                              payment_method="Tiền mặt")
    ]
    inventory_valuation = [
        InventoryReportDTO(product_name="Bút bi Thiên Long", unit_name="Cây", stock_quantity=200,
                           mac_price=Decimal('4000'), total_inventory_value=Decimal('800000'))
    ]
    return DashboardReportDTO(
        kpis=kpis,
        revenue_trend=revenue_trend,
        top_products=top_products,
        transactions=transactions,
        inventory_valuation=inventory_valuation
    )


@pytest.fixture
def report_window(qtbot, mocker, sample_dashboard_dto):
    """Khởi tạo ReportManagementController gắn Mock Service và đăng ký với qtbot"""
    mock_service = mocker.Mock(spec=ReportService)

    mock_service.get_dashboard_report.return_value = sample_dashboard_dto

    window = ReportManagementController(report_service=mock_service)
    qtbot.addWidget(window)

    window.mock_service = mock_service
    return window


# ==========================================
# KIỂM THỬ NHÓM CHẶN LỖI UI (PRE-CONDITIONS)
# ==========================================

def test_should_show_warning_and_prevent_load_when_start_date_is_greater_than_end_date(qtbot, report_window, mocker):
    """TC_UI_Pre_01: Chỉnh ngày bắt đầu lớn hơn ngày kết thúc, bấm LỌC phải hiện Warning và chặn gọi Backend"""
    window = report_window
    window.mock_service.reset_mock()  # Reset lượt gọi tự động từ hàm khởi tạo ban đầu

    # Popup cảnh báo QMessageBox.warning dùng cơ chế bọc lỗi
    mock_warning = mocker.patch('app.modules.report.ui.controllers.report_management_controller.QMessageBox.warning')

    # GIVEN: Người dùng đặt ngày bắt đầu (17/05) lớn hơn ngày kết thúc (16/05)
    window.ui.date_from.setDate(QDate(2026, 5, 17))
    window.ui.date_to.setDate(QDate(2026, 5, 16))

    # WHEN: Người dùng bấm nút "LỌC"
    qtbot.mouseClick(window.ui.btn_run_filter, Qt.MouseButton.LeftButton)

    # THEN: Xuất hiện hộp thoại cảnh báo nghiêm ngặt và tuyệt đối không đẩy lệnh xuống tầng dưới
    mock_warning.assert_called_once_with(window, "Lỗi bộ lọc", "Ngày bắt đầu không được lớn hơn ngày kết thúc!")
    window.mock_service.get_dashboard_report.assert_not_called()


# ==========================================
# KIỂM THỬ ĐỔ DỮ LIỆU THÀNH CÔNG (POST-CONDITIONS)
# ==========================================

def test_should_sync_dates_and_trigger_exclusive_button_states_when_quick_filter_is_clicked(qtbot, report_window):
    """TC_UI_Post_01: Click nút bộ lọc nhanh phải đồng bộ thời gian và kích hoạt tải báo cáo"""
    window = report_window
    window.mock_service.reset_mock()

    # WHEN: Người dùng click vào nút lọc nhanh "Hôm qua"
    qtbot.mouseClick(window.ui.btn_filter_yesterday, Qt.MouseButton.LeftButton)

    # THEN: 1. Hệ thống phải thực thi lệnh gọi xuống backend ngay lập tức
    window.mock_service.get_dashboard_report.assert_called_once()

    # THEN: 2. Ràng buộc độc quyền QButtonGroup: Nút "Hôm qua" sáng, các nút còn lại phải tự động nhả ra
    assert window.ui.btn_filter_yesterday.isChecked() is True
    assert window.ui.btn_filter_today.isChecked() is False
    assert window.ui.btn_filter_month.isChecked() is False


def test_should_populate_kpi_cards_tables_and_render_charts_on_successful_data_load(qtbot, report_window,
                                                                                    sample_dashboard_dto):
    """TC_UI_Post_02: Đổ dữ liệu thành công phải format tiền tệ, hiển thị bảng (canh lề chuẩn) và dựng biểu đồ"""
    window = report_window

    # WHEN: Kích hoạt trực tiếp luồng nạp dữ liệu thành công
    window.load_report_data("2026-05-15", "2026-05-16")

    # THEN: 1. Kiểm chứng Thẻ KPI (KPI Cards) - Số tiền hiển thị phải định dạng dấu phẩy phân cách hàng ngàn mẫu đẹp
    assert window.ui.val_revenue.text() == "500,000 VND"
    assert window.ui.val_profit.text() == "210,000 VND"
    assert window.ui.val_orders.text() == "3"
    assert window.ui.val_stock_value.text() == "1,100,000 VND"

    # THEN: 2. Kiểm chứng Bảng Lịch sử giao dịch (tbl_transactions)
    table_trans = window.ui.tbl_transactions
    assert table_trans.rowCount() == 1
    assert table_trans.item(0, 0).text() == "HD003"
    assert table_trans.item(0, 1).text() == "2026-05-16 10:00"

    # Kiểm tra ô số tiền mặt: Phải format đẹp và ép căn phải + căn giữa chiều dọc đúng thiết kế giao diện POS
    amount_item = table_trans.item(0, 2)
    assert amount_item.text() == "150,000"
    assert amount_item.textAlignment() == (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    assert table_trans.item(0, 3).text() == "Tiền mặt"

    # THEN: 3. Kiểm chứng Bảng Báo cáo tồn kho (tbl_inventory_report)
    table_inv = window.ui.tbl_inventory_report
    assert table_inv.rowCount() == 1
    assert table_inv.item(0, 0).text() == "Bút bi Thiên Long"
    # Cột đơn vị tính và số lượng tồn kho bắt buộc phải được căn giữa (AlignCenter)
    assert table_inv.item(0, 1).textAlignment() == Qt.AlignmentFlag.AlignCenter
    assert table_inv.item(0, 2).textAlignment() == Qt.AlignmentFlag.AlignCenter
    assert table_inv.item(0, 2).text() == "200"
    assert table_inv.item(0, 4).text() == "800,000"

    # THEN: 4. Kiểm chứng Nhúng biểu đồ Matplotlib Đồ họa
    # Các khung layout placeholder ban đầu rỗng, sau khi render thành công bắt buộc số phần tử widget con phải > 0
    assert window.ui.chart_revenue.layout().count() > 0
    assert window.ui.chart_top_products.layout().count() > 0


# ==========================================
# KIỂM THỬ TÍNH BẤT BIẾN & KHÁNG SẬP (UI INVARIANTS)
# ==========================================

def test_should_show_critical_system_error_and_prevent_application_crash_when_backend_fails(qtbot, report_window,
                                                                                            mocker):
    """TC_UI_Inv_01: Khi Backend sập / Connection Timeout, UI phải bắt exception, chìa thông báo lỗi văn minh, cấm văng app"""
    window = report_window

    # GIVEN: Giả lập tình huống nghiêm trọng - Backend bị timeout kỹ thuật ném lỗi bùng nổ
    window.mock_service.get_dashboard_report.side_effect = Exception("MySQL Server Connection Lost!")

    # Tóm sống hộp thoại thông báo lỗi hệ thống QMessageBox.critical
    mock_critical = mocker.patch('app.modules.report.ui.controllers.report_management_controller.QMessageBox.critical')

    # WHEN: Thực hiện gọi tải dữ liệu trong trạng thái lỗi mạng
    window.load_report_data("2026-05-15", "2026-05-16")

    # THEN: 1. Hộp thoại thông báo lỗi đỏ phải chìa ra cho khách hàng nhìn thấy
    mock_critical.assert_called_once()

    # THEN: 2. Nội dung thông báo lỗi của Backend phải được hiển thị tường minh, phục vụ đắc lực việc khoanh vùng vết bug (Traceback)
    assert "MySQL Server Connection Lost!" in mock_critical.call_args[0][2]