# tests/dashboard/test_home_welcome_controller.py
import pytest
from PyQt6.QtCore import Qt
from app.modules.dashboard.ui.controllers.dashboard_controller import HomeWelcomeController


class DummyKPI:
    def __init__(self): self.total_orders_completed = 1550  # Định dạng test số lớn phân tách dấu phẩy


class DummyReportData:
    def __init__(self): self.kpis = DummyKPI()


@pytest.fixture
def mock_services(mocker):
    """Mock toàn bộ biên giới Services để cô lập giao diện PyQt6"""
    return {
        "report": mocker.Mock(),
        "inventory": mocker.Mock(),
        "tax": mocker.Mock(),
        "log": mocker.Mock()
    }


@pytest.fixture
def dashboard_ui(qtbot, mock_services):
    # Cài đặt dữ liệu mồi mặc định cho các mock service
    mock_services["report"].get_dashboard_report.return_value = DummyReportData()
    mock_services["log"].get_daily_activity_feed.return_value = ["[10:00] 🛒 Hóa đơn #HD-01: Hoàn tất"]
    mock_services["inventory"].get_inventory_list.return_value = []
    mock_services["tax"].get_tax_warning_status.return_value = {"percent": 45.2, "is_near_threshold": False}

    # Khởi tạo widget giao diện
    controller = HomeWelcomeController(
        report_service=mock_services["report"],
        inventory_service=mock_services["inventory"],
        tax_service=mock_services["tax"],
        activity_log_service=mock_services["log"]
    )
    qtbot.addWidget(controller)
    return controller


# --- TEST CASES ---
def test_should_render_badges_and_live_feed_correctly(dashboard_ui):
    """UC_UI_1 & UC_UI_2: Vẽ chính xác các con số lên Badge và ném dữ liệu vào ListWidget"""
    # THEN: Kiểm tra hiển thị dấu phẩy phân tách hàng nghìn của Badge Đơn hàng
    assert dashboard_ui.ui.val_badge_orders.text() == "1,550 hóa đơn"
    assert dashboard_ui.ui.val_badge_tax.text() == "45.2%"

    # THEN: Kiểm tra dữ liệu nạp vào dòng thời gian Live Feed
    assert dashboard_ui.ui.list_live_feed.count() == 1
    assert "🛒 Hóa đơn #HD-01" in dashboard_ui.ui.list_live_feed.item(0).text()


def test_should_trigger_deep_linking_signal_when_alert_clicked(qtbot, dashboard_ui, mock_services):
    """UC_UI_4: Click vào nhiệm vụ kho sắp hết phải bắn ra tín hiệu chuyển trang (Deep linking)"""

    # GIVEN: Ép Service kho trả về 1 mặt hàng chạm đáy định mức tối thiểu
    class MockInventoryItem:
        sku = "TL-02"
        product_name = "Bút Thiên Long"
        is_low_stock = True

    mock_services["inventory"].get_inventory_list.return_value = [MockInventoryItem()]

    # Refresh lại màn hình để bắt cấu hình mới
    dashboard_ui.refresh_dashboard()

    # Đảm bảo bảng nhiệm vụ sinh ra dòng cảnh báo vạch đỏ nhấn mạnh
    assert dashboard_ui.ui.list_actionable_alerts.count() == 1

    # Kỹ thuật bắt Signal (Tín hiệu Qt):
    # Đăng ký lắng nghe sự kiện navigation_requested xem có bắn ra đúng (target_tab=2, search_key='TL-02')
    with qtbot.waitSignal(dashboard_ui.navigation_requested, timeout=1000) as blocker:
        # WHEN: Con bot giả lập click chuột trái vào dòng cảnh báo hàng sắp hết trên UI
        item_widget = dashboard_ui.ui.list_actionable_alerts.item(0)
        dashboard_ui.ui.list_actionable_alerts.itemClicked.emit(item_widget)

    # THEN: Xác nhận tín hiệu liên kết sâu truyền tải tham số chính xác tuyệt đối
    assert blocker.args == [2, "TL-02"]