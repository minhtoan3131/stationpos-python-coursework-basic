import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

# Import các DTO hoặc tạo class giả để làm data mồi
from app.modules.home_wellcome.ui.controllers.home_welcome_controller import HomeWelcomeController


# =========================================================================
# FIXTURES
# =========================================================================

@pytest.fixture
def mock_services(mocker):
    """Tạo ra 3 Service giả (Mock) để bơm vào Controller"""
    report_service = mocker.MagicMock()
    inventory_service = mocker.MagicMock()
    tax_service = mocker.MagicMock()
    return report_service, inventory_service, tax_service


@pytest.fixture
def home_controller(qtbot, mock_services, mocker):
    """Khởi tạo Controller với các Service đã bị Mock"""
    report_service, inventory_service, tax_service = mock_services

    # GIVEN cơ bản: Thiết lập dữ liệu an toàn mặc định để hàm __init__ chạy trơn tru
    # Mock Report
    mock_dashboard = mocker.MagicMock()
    mock_dashboard.kpis.total_orders = 15
    report_service.get_dashboard_report.return_value = mock_dashboard
    report_service.get_daily_activity_feed.return_value = []

    # Mock Inventory
    inventory_service.get_inventory_list.return_value = []

    # Mock Tax
    tax_service.get_tax_warning_status.return_value = {
        "revenue": 50000000,
        "threshold": 1000000000,
        "percent": 5.0,
        "is_near_threshold": False
    }

    # Bơm mock vào Controller
    controller = HomeWelcomeController(report_service, inventory_service, tax_service)

    # Đăng ký widget với qtbot để tự động dọn dẹp sau khi test xong
    qtbot.addWidget(controller)

    return controller, mock_services


# =========================================================================
# TEST CASES
# =========================================================================

def test_refresh_dashboard_safe_state(qtbot, home_controller):
    """Kiểm tra màn hình hiển thị trạng thái AN TOÀN khi không có cảnh báo nào"""
    controller, _ = home_controller

    # GIVEN: Các mock service mặc định trả về mảng rỗng (Kho đủ, Thuế thấp) -> Đã set ở fixture

    # WHEN: Gọi hàm làm mới giao diện
    controller.refresh_dashboard()

    # THEN:
    # 1. Badge số đơn hàng phải là 15
    assert controller.ui.val_badge_orders.text() == "15 hóa đơn"

    # 2. Badge kho và thuế phải là số 0 hoặc an toàn
    assert controller.ui.val_badge_stock.text() == "0 sản phẩm"
    assert controller.ui.val_badge_tax.text() == "5.0%"

    # 3. Bảng cảnh báo bên trái phải có đúng 1 dòng báo an toàn
    assert controller.ui.list_actionable_alerts.count() == 1
    safe_item = controller.ui.list_actionable_alerts.item(0)
    assert "✅ Hệ thống vận hành an toàn" in safe_item.text()


def test_refresh_dashboard_with_alerts(qtbot, home_controller, mocker):
    """Kiểm tra UI hiển thị đúng cảnh báo khi Kho hết hàng và Thuế chạm ngưỡng"""
    controller, (report_srv, inventory_srv, tax_srv) = home_controller

    # GIVEN: Ép Inventory Service trả về 1 sản phẩm bị lỗi
    mock_product = mocker.MagicMock()
    mock_product.is_low_stock = True
    mock_product.sku = "B102"
    mock_product.product_name = "Bút bi"
    inventory_srv.get_inventory_list.return_value = [mock_product]

    # GIVEN: Ép Tax Service trả về cờ cảnh báo nguy hiểm
    tax_srv.get_tax_warning_status.return_value = {
        "revenue": 950000000,
        "threshold": 1000000000,
        "percent": 95.0,
        "is_near_threshold": True
    }

    # WHEN: Làm mới giao diện
    controller.refresh_dashboard()

    # THEN:
    # 1. Bảng cảnh báo phải có 2 dòng (1 Thuế, 1 Kho). KHÔNG CÓ chữ an toàn.
    assert controller.ui.list_actionable_alerts.count() == 2

    # Dòng 0 (Thuế luôn được insert lên đầu bằng insertItem(0, ...))
    tax_item = controller.ui.list_actionable_alerts.item(0)
    assert "⚠️ Cảnh báo Thuế" in tax_item.text()

    # Dòng 1 (Kho)
    stock_item = controller.ui.list_actionable_alerts.item(1)
    assert "🚨 Hàng sắp hết" in stock_item.text()
    assert "B102" in stock_item.text()


def test_handle_alert_click_emits_deep_link_signal(qtbot, home_controller):
    """Kiểm tra macro: Click vào dòng cảnh báo phải bắn Signal mang theo Data điều hướng"""
    controller, _ = home_controller

    # GIVEN: Giả lập một QListWidgetItem đang mang cục data ngầm (UserRole)
    fake_item = QListWidgetItem("🚨 Cảnh báo test")
    fake_item.setData(Qt.ItemDataRole.UserRole, {
        'target_tab': 2,
        'search_key': 'SKU-999'
    })

    # WHEN: Người dùng click vào item (gọi thẳng hàm xử lý sự kiện)
    # Ta dùng khối with qtbot.waitSignal để theo dõi xem signal có được phát ra không
    with qtbot.waitSignal(controller.navigation_requested, timeout=1000) as blocker:
        controller.handle_alert_click(fake_item)

    # THEN: Signal `navigation_requested` PHẢI ĐƯỢC BẮN RA với đúng 2 tham số (2, 'SKU-999')
    assert blocker.args == [2, 'SKU-999']


