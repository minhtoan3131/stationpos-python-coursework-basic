# File: app/modules/sale/ui/controllers/invoice_history_controller.py
import datetime
import traceback
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox, QHeaderView, QAbstractItemView, QInputDialog, QFileDialog
from PyQt6.QtCore import Qt
from app.core.exceptions.validation_exception import ValidationException
from app.modules.sale.utils.invoice_history_excel_exporter import InvoiceHistoryExcelExporter


class InvoiceHistoryController:
    def __init__(self, ui, invoice_history_service):
        self.ui = ui
        self.service = invoice_history_service

        self.selected_invoice = None
        self.cached_invoices = []  # Lưu cache danh sách Master trả về từ DB

        self.setup_tables()
        self.bind_events()
        self.reset_filters_ui()

    def setup_tables(self):
        """Cấu hình hành vi hiển thị cho các bảng dữ liệu lịch sử"""
        self.ui.tbl_invoice_master.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tbl_invoice_master.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tbl_invoice_master.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ui.tbl_invoice_master.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.ui.tbl_invoice_details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tbl_invoice_details.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tbl_invoice_details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ui.tbl_invoice_details.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.ui.splitter_invoice.setSizes([650, 750])

    def bind_events(self):
        self.ui.btn_filter_invoice.clicked.connect(self.load_master_data)
        self.ui.btn_reset_filter_invoice.clicked.connect(self.handle_reset_filters)
        self.ui.txt_search_invoice.returnPressed.connect(self.load_master_data)

        self.ui.tbl_invoice_master.itemSelectionChanged.connect(self.handle_master_selection)

        self.ui.btn_cancel_invoice.clicked.connect(self.handle_cancel_invoice)
        self.ui.btn_reprint_invoice.clicked.connect(self.handle_reprint_invoice)
        self.ui.btn_export_invoice_excel.clicked.connect(self.handle_export_excel)

    def reset_filters_ui(self):
        today = datetime.date.today()
        first_day = today.replace(day=1)
        self.ui.date_invoice_from.setDate(first_day)
        self.ui.date_invoice_to.setDate(today)
        self.ui.txt_search_invoice.clear()

        # Đồng bộ hóa bộ lọc CComboBox với file UI của bạn
        self.ui.cbo_payment_method_filter.setCurrentIndex(0)
        self.ui.cbo_status_invoice.setCurrentIndex(0)


    def load_master_data(self):
        """Đọc bộ lọc trên UI và đổ dữ liệu thật từ Database lên bảng Master bên trái"""
        p_method = None
        if self.ui.cbo_payment_method_filter.currentIndex() == 1:
            p_method = 'CASH'
        elif self.ui.cbo_payment_method_filter.currentIndex() == 2:
            p_method = 'TRANSFER'

        status_val = None
        if self.ui.cbo_status_invoice.currentIndex() == 1:
            status_val = 'COMPLETED'
        elif self.ui.cbo_status_invoice.currentIndex() == 2:
            status_val = 'CANCELLED'

        filters = {
            "keyword": self.ui.txt_search_invoice.text().strip(),
            "date_from": self.ui.date_invoice_from.date().toPyDate(),
            "date_to": self.ui.date_invoice_to.date().toPyDate(),
            "payment_method": p_method,
            "status": status_val
        }

        try:
            # Triển khai lời gọi thực tế xuống Service
            self.cached_invoices = self.service.search_invoices(filters)

            self.ui.tbl_invoice_master.setRowCount(0)
            self.clear_detail_view()
            self.ui.tbl_invoice_master.setRowCount(len(self.cached_invoices))

            for row, inv in enumerate(self.cached_invoices):
                self.ui.tbl_invoice_master.setItem(row, 0, QTableWidgetItem(inv['code']))
                self.ui.tbl_invoice_master.setItem(row, 1,
                                                   QTableWidgetItem(inv['created_at'].strftime("%d/%m/%Y %H:%M")))

                amount_item = QTableWidgetItem(f"{float(inv['final_amount']):,.0f}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.ui.tbl_invoice_master.setItem(row, 2, amount_item)

                method_text = "Tiền mặt" if inv['payment_method'] == 'CASH' else "Chuyển khoản"
                self.ui.tbl_invoice_master.setItem(row, 3, QTableWidgetItem(method_text))

                # Format màu sắc phân cấp trạng thái
                status_text = "Hoàn thành" if inv['status'] == 'COMPLETED' else "Đã hủy"
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if inv['status'] == 'CANCELLED':
                    status_item.setForeground(Qt.GlobalColor.red)
                    font = status_item.font()
                    font.setBold(True)
                    status_item.setFont(font)
                else:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                self.ui.tbl_invoice_master.setItem(row, 4, status_item)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi hệ thống", f"Không thể tải nhật ký hóa đơn:\n{str(e)}")

    def handle_reset_filters(self):
        self.reset_filters_ui()
        self.load_master_data()

    def handle_master_selection(self):
        """Khi click vào 1 hóa đơn -> Gọi Service tải chi tiết thực tế lên Panel bên phải"""
        selected_rows = self.ui.tbl_invoice_master.selectedItems()
        if not selected_rows:
            self.clear_detail_view()
            return

        row_idx = selected_rows[0].row()
        invoice_code = self.ui.tbl_invoice_master.item(row_idx, 0).text()
        self.selected_invoice = invoice_code

        try:
            # Gọi Service lấy trọn vẹn dữ liệu thật từ DB
            invoice_full_data = self.service.get_invoice_full_details(invoice_code)
            meta = invoice_full_data['metadata']
            items = invoice_full_data['items']

            # 1. Điền thông tin Metadata Panel
            self.ui.lbl_md_invoice_id.setText(f"<b>Mã HĐ:</b> {meta['code']}")
            self.ui.lbl_md_invoice_date.setText(f"<b>Ngày bán:</b> {meta['created_at'].strftime('%d/%m/%Y %H:%M')}")

            status_html = "<span style='color:green;'><b>Hoàn thành</b></span>"
            if meta['status'] == 'CANCELLED':
                status_html = f"<span style='color:red;'><b>Đã hủy</b></span> | Lý do: {meta.get('cancel_reason') or 'Không rõ'}"
            self.ui.lbl_md_invoice_status.setText(f"<b>Trạng thái:</b> {status_html}")

            # 2. Cập nhật số tiền hiển thị
            self.ui.lbl_detail_total_value.setText(f"{float(meta['final_amount']):,.0f} VND")
            self.ui.lbl_detail_cash_received_label.setText(f"Tiền khách đưa: {float(meta['cash_received']):,.0f} VND")

            # 3. Đổ dữ liệu sản phẩm chi tiết vào bảng phải
            self.ui.tbl_invoice_details.setRowCount(0)
            self.ui.tbl_invoice_details.setRowCount(len(items))
            for r, item in enumerate(items):
                self.ui.tbl_invoice_details.setItem(r, 0, QTableWidgetItem(item['product_name']))

                unit_item = QTableWidgetItem(item['unit_name'])
                unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_invoice_details.setItem(r, 1, unit_item)

                qty_item = QTableWidgetItem(str(item['quantity']))
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_invoice_details.setItem(r, 2, qty_item)

                price_item = QTableWidgetItem(f"{float(item['unit_price']):,.0f}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.ui.tbl_invoice_details.setItem(r, 3, price_item)

                total_item = QTableWidgetItem(f"{float(item['total_price']):,.0f}")
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.ui.tbl_invoice_details.setItem(r, 4, total_item)

            # 4. Quản lý quyền nút hành động (Chỉ cho hủy nếu trạng thái là COMPLETED)
            self.ui.btn_cancel_invoice.setEnabled(meta['status'] == 'COMPLETED')

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi", f"Không thể hiển thị chi tiết hóa đơn:\n{str(e)}")

    def clear_detail_view(self):
        self.selected_invoice = None
        self.ui.tbl_invoice_details.setRowCount(0)
        self.ui.lbl_md_invoice_id.setText("<b>Mã HĐ:</b> --")
        self.ui.lbl_md_invoice_date.setText("<b>Ngày bán:</b> --")
        self.ui.lbl_md_invoice_status.setText("<b>Trạng thái:</b> --")
        self.ui.lbl_detail_total_value.setText("0 VND")
        self.ui.lbl_detail_cash_received_label.setText("Tiền khách đưa: --")
        self.ui.btn_cancel_invoice.setEnabled(False)

    def handle_cancel_invoice(self):
        """Xử lý hành động bấm nút Hủy Hóa Đơn - Chạy chuẩn Luồng 4 nghiệp vụ"""
        if not self.selected_invoice: return

        reason, ok = QInputDialog.getText(
            None, "Xác nhận hủy hóa đơn",
            f"Bạn đang yêu cầu HỦY hóa đơn {self.selected_invoice}.\n"
            f"Hệ thống sẽ thực hiện pha loãng lại giá vốn và nhập trả lại kho vật lý.\n\n"
            f"Nhập lý do hủy thực tế:"
        )
        if not ok or not reason.strip():
            return

        try:
            # Kích hoạt thực thi Luồng 4
            self.service.execute_cancel_invoice(self.selected_invoice, reason.strip())

            QMessageBox.information(None, "Thành công",
                                    f"Đã hủy hóa đơn {self.selected_invoice} thành công, toàn bộ hàng hóa đã được nhập hoàn kho!")
            self.load_master_data()  # Tải lại danh sách

        except ValidationException as ve:
            QMessageBox.warning(None, "Chặn nghiệp vụ", str(ve))
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi hệ thống", f"Hủy hóa đơn thất bại:\n{str(e)}")

    def handle_reprint_invoice(self):
        if self.selected_invoice:
            self.service.process_reprint_invoice(self.selected_invoice)
            QMessageBox.information(None, "In ấn",
                                    f"Đã gửi lệnh kết xuất in lại hóa đơn {self.selected_invoice} tới driver thành công!")

    def handle_export_excel(self):
        """Xử lý nghiệp vụ xuất File Excel chi tiết thực tế"""
        if not self.selected_invoice:
            return

        # 1. Định nghĩa tên file mặc định dựa trên mã hóa đơn người dùng đang chọn
        default_filename = f"HoaDon_{self.selected_invoice}.xlsx"

        # 2. Mở Hộp thoại lưu file của hệ điều hành (Windows/Mac)
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Xuất Excel Chi tiết Hóa đơn",
            default_filename,
            "Excel Files (*.xlsx);;All Files (*)"
        )

        if file_path:
            # Đảm bảo đuôi file luôn chuẩn hóa .xlsx
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'

            try:
                # Gọi service lấy cấu trúc cục dữ liệu
                raw_data = self.service.export_invoice_to_excel(self.selected_invoice)

                # Thực thi ghi đè dữ liệu tài chính xuống file vật lý thông qua Exporter
                success = InvoiceHistoryExcelExporter.export_detail(
                    file_path=file_path,
                    metadata=raw_data['metadata'],
                    items=raw_data['items']
                )

                if success:
                    QMessageBox.information(
                        None,
                        "Thành công",
                        f"Đã xuất hóa đơn chi tiết thành công tại đường dẫn:\n{file_path}"
                    )
            except Exception as e:
                QMessageBox.critical(
                    None,
                    "Lỗi hệ thống",
                    f"Kết xuất báo cáo Excel thất bại:\n{str(e)}"
                )