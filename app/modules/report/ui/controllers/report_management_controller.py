import traceback
from PyQt6.QtWidgets import (
    QWidget, QHeaderView, QTableWidgetItem, QVBoxLayout, QMessageBox, QAbstractItemView, QButtonGroup
)
from PyQt6.QtCore import Qt, QDate

from app.core.exceptions.validation_exception import ValidationException
from app.modules.report.ui.generated.ui_report_management import Ui_ReportManagementWidget
from app.modules.report.services.report_service import ReportService
from app.modules.report.dtos.report_dto import DashboardReportDTO
from app.modules.report.utils.date_helper import DateHelper
from app.modules.report.utils.chart_builder import ChartBuilder
import matplotlib.pyplot as plt


class ReportManagementController(QWidget):
    def __init__(self, report_service: ReportService):
        super().__init__()
        self.ui = Ui_ReportManagementWidget()
        self.ui.setupUi(self)

        self.report_service = report_service

        self.setup_tables()
        self.setup_button_group()
        self.bind_events()

        # Mặc định tải báo cáo hôm nay khi mở màn hình
        self.handle_filter_today()

    def setup_tables(self):
        """Cấu hình hành vi hiển thị cho các bảng dữ liệu."""
        self.ui.tbl_transactions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tbl_transactions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.ui.tbl_inventory_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tbl_inventory_report.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def bind_events(self):
        """Đăng ký lắng nghe các sự kiện tương tác trên UI."""
        self.ui.btn_filter_today.clicked.connect(self.handle_filter_today)
        self.ui.btn_filter_yesterday.clicked.connect(self.handle_filter_yesterday)
        self.ui.btn_filter_month.clicked.connect(self.handle_filter_month)
        self.ui.btn_run_filter.clicked.connect(self.handle_custom_filter)

    def _sync_ui_dates_and_load(self, start_date: str, end_date: str):
        """Hàm private đồng bộ chuỗi ngày ngược lên widget QDateEdit và kích hoạt tải dữ liệu."""
        self.ui.date_from.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
        self.ui.date_to.setDate(QDate.fromString(end_date, "yyyy-MM-dd"))
        self.load_report_data(start_date, end_date)

    # ==========================================
    # KHU VỰC ĐIỀU PHỐI EVENT BỘ LỌC
    # ==========================================

    def handle_filter_today(self):
        start, end = DateHelper.get_today_range()
        self._sync_ui_dates_and_load(start, end)

    def handle_filter_yesterday(self):
        start, end = DateHelper.get_yesterday_range()
        self._sync_ui_dates_and_load(start, end)

    def handle_filter_month(self):
        start, end = DateHelper.get_this_month_range()
        self._sync_ui_dates_and_load(start, end)

    def handle_custom_filter(self):
        start_date = self.ui.date_from.date().toString("yyyy-MM-dd")
        end_date = self.ui.date_to.date().toString("yyyy-MM-dd")

        if self.ui.date_from.date() > self.ui.date_to.date():
            QMessageBox.warning(self, "Lỗi bộ lọc", "Ngày bắt đầu không được lớn hơn ngày kết thúc!")
            return

        self.filter_btn_group.setExclusive(False)
        self.ui.btn_filter_today.setChecked(False)
        self.ui.btn_filter_yesterday.setChecked(False)
        self.ui.btn_filter_month.setChecked(False)
        self.filter_btn_group.setExclusive(True)

        self.load_report_data(start_date, end_date)

    # ==========================================
    # CẬP NHẬT DỮ LIỆU LÊN GIAO DIỆN
    # ==========================================

    def load_report_data(self, start_date: str, end_date: str):
        try:
            report_data: DashboardReportDTO = self.report_service.get_dashboard_report(start_date, end_date)

            self.update_kpi_cards(report_data.kpis)
            self.update_transaction_table(report_data.transactions)
            self.update_inventory_table(report_data.inventory_valuation)
            self.render_charts(report_data.revenue_trend, report_data.top_products)

        except ValidationException as ve:
            # Lỗi chọn sai ngày của người dùng chỉ hiện Cảnh báo màu vàng thân thiện
            QMessageBox.warning(self, "Lỗi bộ lọc", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Hệ Thống", f"Không thể tải dữ liệu báo cáo thống kê:\n{str(e)}")

    def update_kpi_cards(self, kpis):
        """Đổ dữ liệu kiểm toán chuẩn lên cụm 8 thẻ chỉ số phân loại."""
        # Nhóm 1: Doanh thu & Hóa đơn
        self.ui.val_gross_revenue.setText(f"{kpis.gross_revenue:,.0f} VND")
        self.ui.val_cancelled_value.setText(f"{kpis.cancelled_value:,.0f} VND")
        self.ui.val_net_revenue.setText(f"{kpis.net_revenue:,.0f} VND")

        # Hợp nhất thông số phễu đơn hàng: Tổng (Thành công / Hủy)
        order_stats_text = f"{kpis.total_orders_created} đơn ({kpis.total_orders_completed} / {kpis.total_orders_cancelled})"
        self.ui.val_order_stats.setText(order_stats_text)

        # Nhóm 2: Chi phí & Lợi nhuận
        self.ui.val_cogs.setText(f"{kpis.total_cogs:,.0f} VND")
        self.ui.val_gross_profit.setText(f"{kpis.gross_profit:,.0f} VND")
        self.ui.val_variance_garbage.setText(f"{kpis.variance_garbage:,.0f} VND")
        self.ui.val_net_profit.setText(f"{kpis.net_profit:,.0f} VND")

    def update_transaction_table(self, transactions):
        self.ui.tbl_transactions.setRowCount(0)
        for row, trans in enumerate(transactions):
            self.ui.tbl_transactions.insertRow(row)
            self.ui.tbl_transactions.setItem(row, 0, QTableWidgetItem(trans.invoice_code))
            self.ui.tbl_transactions.setItem(row, 1, QTableWidgetItem(trans.created_at))

            amount_item = QTableWidgetItem(f"{trans.total_amount:,.0f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_transactions.setItem(row, 2, amount_item)

            self.ui.tbl_transactions.setItem(row, 3, QTableWidgetItem(trans.payment_method))

    def update_inventory_table(self, inventory):
        self.ui.tbl_inventory_report.setRowCount(0)
        total_inventory_valuation = 0.0
        for row, item in enumerate(inventory):
            self.ui.tbl_inventory_report.insertRow(row)
            self.ui.tbl_inventory_report.setItem(row, 0, QTableWidgetItem(item.product_name))

            unit_item = QTableWidgetItem(item.unit_name)
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tbl_inventory_report.setItem(row, 1, unit_item)

            qty_item = QTableWidgetItem(str(item.stock_quantity))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tbl_inventory_report.setItem(row, 2, qty_item)

            mac_item = QTableWidgetItem(f"{item.mac_price:,.0f}")
            mac_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_inventory_report.setItem(row, 3, mac_item)

            total_item = QTableWidgetItem(f"{item.total_inventory_value:,.0f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_inventory_report.setItem(row, 4, total_item)

            total_inventory_valuation += float(item.total_inventory_value)

        self.ui.lbl_total_inventory_value.setText(f"Tổng giá trị kho: {total_inventory_valuation:,.0f} VND")

    def render_charts(self, revenue_trend, top_products):
        """Nhận Canvas đồ họa từ Builder và nhúng vào vị trí hiển thị trên UI."""
        plt.close('all')  # Đóng toàn bộ figure cũ chạy ngầm để giải phóng bộ nhớ RAM
        self._clear_layout(self.ui.chart_revenue.layout())
        self._clear_layout(self.ui.chart_top_products.layout())

        # Yêu cầu Builder sản xuất ra các Canvas đồ thị mới dựa trên DTO
        canvas_revenue = ChartBuilder.build_revenue_trend_chart(revenue_trend)
        canvas_top = ChartBuilder.build_top_products_chart(top_products)

        # Gắn đồ thị vào layout placeholder tương ứng trên màn hình
        if self.ui.chart_revenue.layout() is None:
            layout_rev = QVBoxLayout(self.ui.chart_revenue)
            layout_rev.setContentsMargins(0, 0, 0, 0)
        self.ui.chart_revenue.layout().addWidget(canvas_revenue)

        if self.ui.chart_top_products.layout() is None:
            layout_top = QVBoxLayout(self.ui.chart_top_products)
            layout_top.setContentsMargins(0, 0, 0, 0)
        self.ui.chart_top_products.layout().addWidget(canvas_top)

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def setup_button_group(self):
        """Nhóm các nút lọc thời gian lại để chúng hoạt động độc quyền (chỉ 1 nút được Active)"""
        self.filter_btn_group = QButtonGroup(self)
        self.filter_btn_group.addButton(self.ui.btn_filter_today)
        self.filter_btn_group.addButton(self.ui.btn_filter_yesterday)
        self.filter_btn_group.addButton(self.ui.btn_filter_month)

        # setExclusive(True) đảm bảo khi bấm nút này, nút kia sẽ tự động nhả ra
        self.filter_btn_group.setExclusive(True)