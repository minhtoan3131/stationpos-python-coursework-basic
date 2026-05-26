import datetime
from PyQt6.QtWidgets import (
    QTableWidgetItem, QMessageBox, QHeaderView, QAbstractItemView, QInputDialog
)
from PyQt6.QtCore import Qt


# Import Service mới của bạn vào đây
# from app.modules.sale.services.invoice_history_service import InvoiceHistoryService

class InvoiceHistoryController:
    def __init__(self, ui, invoice_history_service):
        self.ui = ui  # Nhận object UI từ SalesManagementController truyền sang
        self.service = invoice_history_service  # Kết nối tới Service độc lập mới

        # Biến trạng thái
        self.is_loaded = False
        self.selected_invoice = None

        self.setup_tables()
        self.bind_events()
        self.reset_filters_ui()

    def setup_tables(self):
        """Cấu hình hành vi cho các bảng (chỉ đọc, chọn cả dòng, co giãn cột)"""
        # Bảng Master (Bên trái)
        self.ui.tbl_invoice_master.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tbl_invoice_master.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tbl_invoice_master.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ui.tbl_invoice_master.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Mã HĐ

        # Bảng Detail (Bên phải)
        self.ui.tbl_invoice_details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tbl_invoice_details.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tbl_invoice_details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ui.tbl_invoice_details.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Tên SP

        self.ui.splitter_invoice.setSizes([500, 500])

    def bind_events(self):
        # Bộ lọc
        self.ui.btn_filter_invoice.clicked.connect(self.load_master_data)
        self.ui.btn_reset_filter_invoice.clicked.connect(self.handle_reset_filters)
        self.ui.txt_search_invoice.returnPressed.connect(self.load_master_data)

        # Chọn 1 dòng -> Hiện chi tiết
        self.ui.tbl_invoice_master.itemSelectionChanged.connect(self.handle_master_selection)

        # Nút hành động liên kết với tầng Service nghiệp vụ
        self.ui.btn_cancel_invoice.clicked.connect(self.handle_cancel_invoice)
        self.ui.btn_reprint_invoice.clicked.connect(self.handle_reprint_invoice)
        self.ui.btn_export_invoice_excel.clicked.connect(self.handle_export_excel)

    def reset_filters_ui(self):
        today = datetime.date.today()
        first_day = today.replace(day=1)
        self.ui.date_invoice_from.setDate(first_day)
        self.ui.date_invoice_to.setDate(today)
        self.ui.txt_search_invoice.clear()
        self.ui.cbo_payment_method_filter.setCurrentIndex(0)
        self.ui.cbo_status_invoice.setCurrentIndex(0)

    def initial_load(self):
        """Được gọi khi người dùng chuyển sang Tab Lịch sử lần đầu tiên"""
        if not self.is_loaded:
            self.load_master_data()
            self.is_loaded = True

    def load_master_data(self):
        """Thu thập dữ liệu từ bộ lọc UI và kích hoạt gọi sang tầng Service."""
        # 1. Thu thập thông tin bộ lọc từ giao diện
        filters = {
            "keyword": self.ui.txt_search_invoice.text().strip(),
            "date_from": self.ui.date_invoice_from.date().toPyDate(),
            "date_to": self.ui.date_invoice_to.date().toPyDate(),
            "payment_method": None if self.ui.cbo_payment_method_filter.currentIndex() == 0 else self.ui.cbo_payment_method_filter.currentText(),
            "status": None if self.ui.cbo_status_invoice.currentIndex() == 0 else self.ui.cbo_status_invoice.currentText()
        }

        # Hiển thị thông báo đang xử lý tìm kiếm theo yêu cầu của bạn
        QMessageBox.information(
            None, "Hệ thống",
            f"Đang gọi hàm service.search_invoices() với các bộ lọc:\n"
            f"- Từ khóa: {filters['keyword']}\n"
            f"- Từ ngày: {filters['date_from']} -> Đến ngày: {filters['date_to']}\n"
            f"- Hình thức: {filters['payment_method']}\n"
            f"- Trạng thái: {filters['status']}"
        )

        # 2. Gọi hàm rỗng ở tầng service
        invoices = self.service.search_invoices(filters)

        # 3. Làm sạch bảng và chuẩn bị đổ dữ liệu thực tế
        self.ui.tbl_invoice_master.setRowCount(0)
        self.clear_detail_view()

        self.ui.tbl_invoice_master.setRowCount(2)  # Tạo 2 dòng trống

        # Dòng 1
        self.ui.tbl_invoice_master.setItem(0, 0, QTableWidgetItem("HD-20231027-001"))
        self.ui.tbl_invoice_master.setItem(0, 1, QTableWidgetItem("27/10/2023 14:30"))
        self.ui.tbl_invoice_master.setItem(0, 2, QTableWidgetItem("150,000"))
        self.ui.tbl_invoice_master.setItem(0, 3, QTableWidgetItem("Tiền mặt"))
        self.ui.tbl_invoice_master.setItem(0, 4, QTableWidgetItem("Hoàn thành"))

        # Dòng 2
        self.ui.tbl_invoice_master.setItem(1, 0, QTableWidgetItem("HD-20231026-099"))
        self.ui.tbl_invoice_master.setItem(1, 1, QTableWidgetItem("26/10/2023 09:10"))
        self.ui.tbl_invoice_master.setItem(1, 2, QTableWidgetItem("210,000"))
        self.ui.tbl_invoice_master.setItem(1, 3, QTableWidgetItem("Tiền mặt"))
        self.ui.tbl_invoice_master.setItem(1, 4, QTableWidgetItem("Đã hủy"))

        # TODO: Khi hàm service được triển khai xong, duyệt danh sách 'invoices'
        # và dùng self.ui.tbl_invoice_master.setItem() để đổ dữ liệu thật lên bảng trái

    def handle_reset_filters(self):
        self.reset_filters_ui()
        self.load_master_data()

    def handle_master_selection(self):
        """Xử lý khi click vào một dòng hóa đơn trên bảng Master tổng quan."""
        selected_rows = self.ui.tbl_invoice_master.selectedItems()
        if not selected_rows:
            self.clear_detail_view()
            return

        row_idx = selected_rows[0].row()
        # Lấy tạm mã hóa đơn từ cột 0 trên giao diện
        invoice_code = self.ui.tbl_invoice_master.item(row_idx, 0).text()
        self.selected_invoice = invoice_code

        # Gọi hàm rỗng lấy chi tiết từ tầng Service
        invoice_full_data = self.service.get_invoice_full_details(invoice_code)

        # TODO: Cập nhật thông tin chi tiết từ dữ liệu thật trả về (invoice_full_data) lên giao diện:
        # - Cập nhật các Label: lbl_md_invoice_id, lbl_md_invoice_date, lbl_md_invoice_status
        # - Cập nhật số tiền: lbl_detail_total_value, lbl_detail_cash_received_label
        # - Điền danh sách mặt hàng vào bảng: tbl_invoice_details
        # - Kiểm tra trạng thái hóa đơn để thiết lập bật/tắt nút hủy:
        #   self.ui.btn_cancel_invoice.setEnabled(trạng_thái != "Đã hủy")

        # Tạm thời bật nút Hủy hóa đơn lên để phục vụ test tính năng bấm nút hành động
        self.ui.btn_cancel_invoice.setEnabled(True)

    def clear_detail_view(self):
        self.selected_invoice = None
        self.ui.tbl_invoice_details.setRowCount(0)
        self.ui.lbl_md_invoice_id.setText("<b>Mã HĐ:</b> --")
        self.ui.lbl_md_invoice_date.setText("<b>Ngày bán:</b> --")
        self.ui.lbl_md_invoice_status.setText("<b>Trạng thái:</b> --")
        self.ui.lbl_detail_total_value.setText("0 VND")
        self.ui.lbl_detail_cash_received_label.setText("Tiền khách đưa: --")
        self.ui.btn_cancel_invoice.setEnabled(False)

    # ==========================================
    # XỬ LÝ CÁC HÀNH ĐỘNG HẬU KỲ (GỌI SERVICE & POPUP)
    # ==========================================
    def handle_cancel_invoice(self):
        """Xử lý nghiệp vụ Hủy Hóa Đơn"""
        if not self.selected_invoice:
            return

        # Hiển thị hộp thoại yêu cầu nhập lý do hủy hóa đơn thực tế
        reason, ok = QInputDialog.getText(None, "Hủy hóa đơn", f"Nhập lý do hủy cho hóa đơn {self.selected_invoice}:")
        if not ok or not reason.strip():
            return

        # Thông báo tượng trưng đang xử lý kết nối Service
        QMessageBox.information(
            None, "Xử lý nghiệp vụ",
            f"Đang gọi hàm service.execute_cancel_invoice()\n"
            f"- Mã hóa đơn: {self.selected_invoice}\n"
            f"- Lý do hủy: {reason}"
        )

        # Gọi hàm xử lý rỗng tại Service
        success = self.service.execute_cancel_invoice(self.selected_invoice, reason)

        # TODO: Sau khi triển khai xong logic Service, tiến hành thông báo thành công,
        # vô hiệu hóa nút hủy và tải lại danh sách dữ liệu mới nhất (self.load_master_data())
        self.ui.btn_cancel_invoice.setEnabled(False)

    def handle_reprint_invoice(self):
        """Xử lý nghiệp vụ In lại hóa đơn"""
        if not self.selected_invoice:
            return

        # Thông báo tượng trưng đang gửi lệnh in
        QMessageBox.information(
            None, "In ấn",
            f"Đang gọi hàm service.process_reprint_invoice() để kết nối Driver kết xuất lệnh in cho mã: {self.selected_invoice}"
        )

        # Gọi hàm in rỗng tại Service
        self.service.process_reprint_invoice(self.selected_invoice)

    def handle_export_excel(self):
        """Xử lý nghiệp vụ Xuất File Excel chi tiết"""
        if not self.selected_invoice:
            return

        # Thông báo tượng trưng đang xuất bản tệp tin
        QMessageBox.information(
            None, "Xuất báo cáo",
            f"Đang gọi hàm service.export_invoice_to_excel() để sinh tệp Excel chi tiết của: {self.selected_invoice}"
        )

        # Gọi hàm xuất Excel rỗng tại Service
        file_output_path = self.service.export_invoice_to_excel(self.selected_invoice)

        # Mô phỏng thông báo kết xuất file thành công
        QMessageBox.information(None, "Thành công", f"Đã khởi tạo file mẫu tại hệ thống!")