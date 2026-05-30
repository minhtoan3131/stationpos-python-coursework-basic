# File: app/tests/report/test_ui_report_management.py
import pytest
from decimal import Decimal
from PyQt6.QtCore import Qt, QDate

from app.modules.report.ui.controllers.report_management_controller import ReportManagementController
from app.modules.report.services.report_service import ReportService
from app.modules.report.dtos.report_dto import (
    DashboardReportDTO, KPIDTO, RevenueTrendItemDTO,
    TopProductDTO, TransactionHistoryDTO, InventoryReportDTO
)


# =========================================================================
# THIẾT LẬP MÔI TRƯỜNG MOCK ĐỂ KIỂM THỬ HỘP ĐEN TẦNG UI ( ĐÚNG 8 CHỈ SỐ )
# =========================================================================

@pytest.fixture
def sample_dashboard_dto():
    """Tạo gói dữ liệu DTO mẫu toàn vẹn chứa đúng 8 chỉ số mới để ép lên UI."""
    kpis = KPIDTO(
        total_orders_created=4,
        total_orders_completed=3,
        total_orders_cancelled=1,
        gross_revenue=Decimal('550000'),
        cancelled_value=Decimal('50000'),
        net_revenue=Decimal('500000'),
        total_cogs=Decimal('290000'),
        gross_profit=Decimal('210000'),
        variance_garbage=Decimal('-2000'),
        net_profit=Decimal('208000')
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
        TransactionHistoryDTO(invoice_code="HD003", created_at="2026-05-16 10:00", total_amount=Decimal('150000'),
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
    """Khởi tạo Controller, gắn Mock Service chặn gọi DB thật và đăng ký với qtbot"""
    mock_service = mocker.Mock(spec=ReportService)
    mock_service.get_dashboard_report.return_value = sample_dashboard_dto

    window = ReportManagementController(report_service=mock_service)
    qtbot.addWidget(window)

    window.mock_service = mock_service
    return window


# ==========================================
# CÁC KỊCH BẢN KIỂM THỬ GIAO DIỆN HỘP ĐEN
# ==========================================

def test_should_show_warning_and_prevent_load_when_start_date_is_greater_than_end_date(qtbot, report_window, mocker):
    """TC_UI_Pre_01: Đặt ngày bắt đầu > ngày kết thúc, bấm LỌC phải hiện QMessageBox chặn hạ tầng"""
    window = report_window
    window.mock_service.reset_mock()

    mock_warning = mocker.patch('app.modules.report.ui.controllers.report_management_controller.QMessageBox.warning')

    # Người dùng chỉnh ngày sai logic
    window.ui.date_from.setDate(QDate(2026, 5, 17))
    window.ui.date_to.setDate(QDate(2026, 5, 16))

    # Click nút LỌC
    qtbot.mouseClick(window.ui.btn_run_filter, Qt.MouseButton.LeftButton)

    # Khẳng định: Hiện cảnh báo và chặn đứng không cho gọi xuống Service
    mock_warning.assert_called_once_with(window, "Lỗi bộ lọc", "Ngày bắt đầu không được lớn hơn ngày kết thúc!")
    window.mock_service.get_dashboard_report.assert_not_called()


def test_should_sync_dates_and_trigger_exclusive_button_states_when_quick_filter_is_clicked(qtbot, report_window):
    """TC_UI_Post_01: Bấm nút lọc nhanh 'Hôm qua' phải đồng bộ ngày và kích hoạt tải dữ liệu"""
    window = report_window
    window.mock_service.reset_mock()

    qtbot.mouseClick(window.ui.btn_filter_yesterday, Qt.MouseButton.LeftButton)

    # Đảm bảo lệnh tải được phát đi và trạng thái nút bấm loại trừ nhau chuẩn xác
    window.mock_service.get_dashboard_report.assert_called_once()
    assert window.ui.btn_filter_yesterday.isChecked() is True
    assert window.ui.btn_filter_today.isChecked() is False


def test_should_populate_kpi_cards_tables_and_render_charts_on_successful_data_load(qtbot, report_window):
    """
    TC_UI_Post_02: Đổ dữ liệu thành công phải hiển thị chuẩn xác biểu mẫu định dạng chuỗi
    lên trọn vẹn 8 thẻ chỉ số phân loại mới (Gross, Cancelled, Net, COGS, Profit,...)
    """
    window = report_window

    # Thực thi nạp chuỗi mồi thành công
    window.load_report_data("2026-05-15", "2026-05-16")

    # 1. Kiểm duyệt Nhóm Doanh thu & Hóa đơn (Hàng 1 trên UI)
    assert window.ui.val_gross_revenue.text() == "550,000 VND"
    assert window.ui.val_cancelled_value.text() == "50,000 VND"
    assert window.ui.val_net_revenue.text() == "500,000 VND"
    assert window.ui.val_order_stats.text() == "4 đơn (3 / 1)"

    # 2. Kiểm duyệt Nhóm Chi phí & Lợi nhuận (Hàng 2 trên UI)
    assert window.ui.val_cogs.text() == "290,000 VND"
    assert window.ui.val_gross_profit.text() == "210,000 VND"
    assert window.ui.val_variance_garbage.text() == "-2,000 VND"
    assert window.ui.val_net_profit.text() == "208,000 VND"

    # 3. Kiểm duyệt Bảng Lịch sử hóa đơn
    table_trans = window.ui.tbl_transactions
    assert table_trans.rowCount() == 1
    assert table_trans.item(0, 0).text() == "HD003"
    assert table_trans.item(0, 2).text() == "150,000"
    assert table_trans.item(0, 2).textAlignment() == (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    # 4. Kiểm duyệt Bảng Báo cáo tồn kho vật lý phía dưới
    table_inv = window.ui.tbl_inventory_report
    assert table_inv.rowCount() == 1
    assert table_inv.item(0, 0).text() == "Bút bi Thiên Long"
    assert table_inv.item(0, 2).text() == "200"
    assert table_inv.item(0, 4).text() == "800,000"

    # 5. Kiểm duyệt Canvas biểu đồ được dựng nhúng thành công
    assert window.ui.chart_revenue.layout().count() > 0
    assert window.ui.chart_top_products.layout().count() > 0


def test_should_show_critical_system_error_and_prevent_application_crash_when_backend_fails(qtbot, report_window, mocker):
    """TC_UI_Inv_01: Khi Service ném lỗi hệ thống, UI phải bắt exception hiện thông báo đỏ, cấm văng App"""
    window = report_window

    window.mock_service.get_dashboard_report.side_effect = Exception("Database Timeout Exception!")
    mock_critical = mocker.patch('app.modules.report.ui.controllers.report_management_controller.QMessageBox.critical')

    window.load_report_data("2026-05-15", "2026-05-16")

    # Xuất hiện hộp thoại báo lỗi nghiêm trọng văn minh, không làm sập ứng dụng PyQt6
    mock_critical.assert_called_once()
    assert "Database Timeout Exception!" in mock_critical.call_args[0][2]