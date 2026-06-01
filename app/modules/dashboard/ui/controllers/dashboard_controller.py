import datetime
import traceback
from PyQt6.QtWidgets import QWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal

from app.modules.dashboard.ui.generated.ui_dashboard import Ui_DashboardWidget


class HomeWelcomeController(QWidget):
    navigation_requested = pyqtSignal(int, str)

    def __init__(self, report_service, inventory_service, tax_service, activity_log_service):
        super().__init__()
        self.ui = Ui_DashboardWidget()
        self.ui.setupUi(self)

        self.report_service = report_service
        self.inventory_service = inventory_service
        self.tax_service = tax_service
        self.activity_log_service = activity_log_service

        self.setup_ui_custom()
        self.bind_events()
        self.refresh_dashboard()

    def setup_ui_custom(self):
        self.ui.list_actionable_alerts.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.list_live_feed.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def bind_events(self):
        self.ui.list_actionable_alerts.itemClicked.connect(self.handle_alert_click)

    def refresh_dashboard(self):
        try:
            current_date_str = datetime.datetime.now().strftime('%Y-%m-%d')
            current_year = datetime.datetime.now().year

            # =========================================================================
            # Chỉ lấy KPI Badge đơn hàng
            # =========================================================================
            report_data = self.report_service.get_dashboard_report(current_date_str, current_date_str)
            total_orders = report_data.kpis.total_orders_completed if report_data and report_data.kpis else 0
            self.ui.val_badge_orders.setText(f'{total_orders:,} hóa đơn')

            # =========================================================================
            # Đọc dữ liệu Timeline từ dịch vụ kiểm toán mới
            # =========================================================================
            self.ui.list_live_feed.clear()
            activities_feed = self.activity_log_service.get_daily_activity_feed(current_date_str)

            if activities_feed:
                for feed_text in activities_feed:
                    self.ui.list_live_feed.addItem(QListWidgetItem(feed_text))
            else:
                self.ui.list_live_feed.addItem(
                    QListWidgetItem('Hôm nay hệ thống chưa ghi nhận biến động sự kiện nào.'))

            # =========================================================================
            # INVENTORY SERVICE: Cảnh báo kho
            # =========================================================================
            inventory_list = self.inventory_service.get_inventory_list()
            low_stock_count = 0

            self.ui.list_actionable_alerts.clear()
            for item in inventory_list:
                if item.is_low_stock:
                    low_stock_count += 1
                    alert_text = f'🚨 Hàng sắp hết: Mã [{item.sku}] ({item.product_name}) đã chạm định mức tối thiểu. Đề xuất lập phiếu nhập kho!'
                    list_item = QListWidgetItem(alert_text)
                    list_item.setData(Qt.ItemDataRole.UserRole, {'target_tab': 2, 'search_key': item.sku})
                    self.ui.list_actionable_alerts.addItem(list_item)

            self.ui.val_badge_stock.setText(f'{low_stock_count} sản phẩm')

            # =========================================================================
            # TAX SERVICE: Cảnh báo thuế
            # =========================================================================
            tax_status = self.tax_service.get_tax_warning_status(current_year)
            self.ui.val_badge_tax.setText(f"{tax_status['percent']:.1f}%")

            if tax_status['is_near_threshold']:
                tax_alert_text = f"⚠️ Cảnh báo Thuế: Doanh thu tích lũy năm ({tax_status['revenue']:,.0f} VND) dự đoán đã tiệm cận hoặc vượt mức miễn thuế ({tax_status['threshold']:,.0f} VND)!"
                tax_item = QListWidgetItem(tax_alert_text)
                tax_item.setData(Qt.ItemDataRole.UserRole, {'target_tab': 5, 'search_key': ''})
                self.ui.list_actionable_alerts.insertItem(0, tax_item)

            if self.ui.list_actionable_alerts.count() == 0:
                self.ui.list_actionable_alerts.addItem(
                    QListWidgetItem('✅ Hệ thống vận hành an toàn: Hiện kho đầy đủ định mức và dòng tiền ổn định.'))

        except Exception as e:
            print('[HomeWelcomeController] Lỗi nghiêm trọng khi tổng hợp dữ liệu Dashboard:')
            traceback.print_exc()

    def handle_alert_click(self, item):
        nav_data = item.data(Qt.ItemDataRole.UserRole)
        if nav_data:
            self.navigation_requested.emit(nav_data.get('target_tab'), nav_data.get('search_key', ''))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_dashboard()