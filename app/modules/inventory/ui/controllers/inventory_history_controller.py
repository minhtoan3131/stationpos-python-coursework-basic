import datetime
import traceback
from PyQt6.QtWidgets import (
    QTableWidgetItem, QMessageBox, QInputDialog,
    QFileDialog, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt

from app.modules.inventory.dtos.po_history_dto import PurchaseOrderHistoryFilterDTO
from app.modules.inventory.services.po_history_service import PurchaseOrderHistoryService
from app.modules.inventory.utils.po_history_excel_exporter import PoHistoryExcelExporter


class InventoryHistoryController:
    def __init__(self, ui, po_history_service: PurchaseOrderHistoryService):
        self.ui = ui  # Nhận toàn bộ object UI từ Controller chính truyền sang
        self.po_history_service = po_history_service

        self.current_po_list = []  # Lưu cache danh sách Master
        self.current_po_details = []  # Lưu cache danh sách Detail
        self.selected_po_master = None  # Trạng thái phiếu đang được chọn
        self.is_loaded = False  # Cờ đánh dấu đã load dữ liệu lần đầu chưa

        self.setup_tables()
        self.bind_events()
        self.reset_filters_ui()

    def setup_tables(self):
        """Cấu hình hành vi cho các bảng (chỉ đọc, chọn cả dòng, co giãn cột)"""
        # Bảng Master (Bên trái)
        self.ui.tbl_po_master.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tbl_po_master.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tbl_po_master.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ui.tbl_po_master.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Cột NCC

        # Bảng Detail (Bên phải)
        self.ui.tbl_po_details.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.tbl_po_details.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.tbl_po_details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ui.tbl_po_details.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Cột Tên SP

    def bind_events(self):
        # Nút bấm bộ lọc
        self.ui.btn_filter_po.clicked.connect(self.load_master_data)
        self.ui.btn_reset_filter_po.clicked.connect(self.handle_reset_filters)
        self.ui.txt_search_po.returnPressed.connect(self.load_master_data)

        # Chọn 1 dòng trên bảng Master -> Hiện chi tiết
        self.ui.tbl_po_master.itemSelectionChanged.connect(self.handle_master_selection)

        # Nút hành động
        self.ui.btn_cancel_po.clicked.connect(self.handle_cancel_po)
        self.ui.btn_export_po_excel.clicked.connect(self.handle_export_excel)

    def reset_filters_ui(self):
        """Đưa các bộ lọc về mặc định (Từ đầu tháng đến hôm nay)"""
        today = datetime.date.today()
        first_day = today.replace(day=1)

        self.ui.date_po_from.setDate(first_day)
        self.ui.date_po_to.setDate(today)
        self.ui.txt_search_po.clear()

        self.ui.cbo_status_po.clear()
        self.ui.cbo_status_po.addItem("Tất cả trạng thái", "ALL")
        self.ui.cbo_status_po.addItem("Hoàn thành", "COMPLETED")
        self.ui.cbo_status_po.addItem("Đã hủy", "CANCELLED")

    def initial_load(self):
        """Được gọi bởi Controller chính khi người dùng lần đầu tiên bấm sang Tab này"""
        if not self.is_loaded:
            self.load_master_data()
            self.is_loaded = True

    # ==========================================
    # LOGIC LOAD DỮ LIỆU
    # ==========================================
    def load_master_data(self):
        # Thu thập điều kiện lọc
        filter_dto = PurchaseOrderHistoryFilterDTO(
            from_date=self.ui.date_po_from.date().toString("yyyy-MM-dd"),
            to_date=self.ui.date_po_to.date().toString("yyyy-MM-dd"),
            keyword=self.ui.txt_search_po.text().strip(),
            status=self.ui.cbo_status_po.currentData()
        )

        try:
            # Gọi Service
            self.current_po_list = self.po_history_service.search_history(filter_dto)

            # Đổ lên bảng
            self.ui.tbl_po_master.setRowCount(0)
            self.ui.tbl_po_master.setRowCount(len(self.current_po_list))

            for row, po in enumerate(self.current_po_list):
                self.ui.tbl_po_master.setItem(row, 0, QTableWidgetItem(po.code))
                self.ui.tbl_po_master.setItem(row, 1, QTableWidgetItem(po.created_at.strftime("%d/%m/%Y %H:%M")))
                self.ui.tbl_po_master.setItem(row, 2, QTableWidgetItem(po.supplier_name))

                amount_item = QTableWidgetItem(f"{po.total_amount:,.0f}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.ui.tbl_po_master.setItem(row, 3, amount_item)

                # Format màu sắc Trạng thái
                status_text = "Hoàn thành" if po.status == 'COMPLETED' else "Đã hủy"
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if po.status == 'CANCELLED':
                    status_item.setForeground(Qt.GlobalColor.red)
                    font = status_item.font()
                    font.setBold(True)
                    status_item.setFont(font)
                else:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)

                self.ui.tbl_po_master.setItem(row, 4, status_item)

            # Reset bảng Detail
            self.clear_detail_view()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi", f"Không thể tải danh sách phiếu nhập:\n{str(e)}")

    def handle_reset_filters(self):
        self.reset_filters_ui()
        self.load_master_data()

    def handle_master_selection(self):
        selected_rows = self.ui.tbl_po_master.selectedItems()
        if not selected_rows:
            self.clear_detail_view()
            return

        row_idx = selected_rows[0].row()
        self.selected_po_master = self.current_po_list[row_idx]

        # Cập nhật Label Meta (Đổi màu nếu hủy)
        self.ui.lbl_md_po_id.setText(f"<b>Mã phiếu:</b> {self.selected_po_master.code}")
        self.ui.lbl_md_date.setText(f"<b>Ngày lập:</b> {self.selected_po_master.created_at.strftime('%d/%m/%Y %H:%M')}")

        note_text = self.selected_po_master.note or "---"
        if self.selected_po_master.status == 'CANCELLED':
            note_text += f" | <span style='color:red;'><b>LÝ DO HỦY:</b> {self.selected_po_master.cancel_reason}</span>"
        self.ui.lbl_md_note.setText(f"<b>Ghi chú:</b> {note_text}")

        self.ui.lbl_detail_total_value.setText(f"{self.selected_po_master.total_amount:,.0f} VND")

        # Quản lý nút Hủy phiếu (Chỉ bật khi phiếu COMPLETED)
        self.ui.btn_cancel_po.setEnabled(self.selected_po_master.status == 'COMPLETED')
        self.ui.btn_export_po_excel.setEnabled(True)

        # Kéo dữ liệu Detail
        try:
            self.current_po_details = self.po_history_service.get_details(self.selected_po_master.id)
            self.ui.tbl_po_details.setRowCount(0)
            self.ui.tbl_po_details.setRowCount(len(self.current_po_details))

            for r, item in enumerate(self.current_po_details):
                self.ui.tbl_po_details.setItem(r, 0, QTableWidgetItem(item.sku))
                self.ui.tbl_po_details.setItem(r, 1, QTableWidgetItem(item.product_name))

                unit_item = QTableWidgetItem(item.unit_name)
                unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_po_details.setItem(r, 2, unit_item)

                qty_item = QTableWidgetItem(f"{item.quantity:,}")
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tbl_po_details.setItem(r, 3, qty_item)

                price_item = QTableWidgetItem(f"{item.unit_price:,.0f}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.ui.tbl_po_details.setItem(r, 4, price_item)

                total_item = QTableWidgetItem(f"{item.total_price:,.0f}")
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.ui.tbl_po_details.setItem(r, 5, total_item)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi", f"Không thể tải chi tiết phiếu nhập:\n{str(e)}")

    def clear_detail_view(self):
        self.selected_po_master = None
        self.current_po_details = []
        self.ui.tbl_po_details.setRowCount(0)
        self.ui.lbl_md_po_id.setText("<b>Mã phiếu:</b> --")
        self.ui.lbl_md_date.setText("<b>Ngày lập:</b> --")
        self.ui.lbl_md_note.setText("<b>Ghi chú:</b> --")
        self.ui.lbl_detail_total_value.setText("0 VND")
        self.ui.btn_cancel_po.setEnabled(False)
        self.ui.btn_export_po_excel.setEnabled(False)

    # ==========================================
    # XỬ LÝ HÀNH ĐỘNG HẬU KỲ
    # ==========================================
    def handle_cancel_po(self):
        if not self.selected_po_master: return

        reason, ok = QInputDialog.getText(
            None, "Xác nhận Hủy phiếu",
            f"Bạn đang chuẩn bị HỦY phiếu nhập {self.selected_po_master.code}.\n\n"
            f"Hệ thống sẽ trừ ngược lại số lượng tồn kho của các sản phẩm trong phiếu.\n\n"
            f"Vui lòng nhập lý do hủy:"
        )

        if ok and reason.strip():
            try:
                self.po_history_service.cancel_purchase_order(self.selected_po_master.id, reason.strip())
                QMessageBox.information(None, "Thành công",
                                        f"Đã hủy phiếu nhập {self.selected_po_master.code} thành công và trừ lại tồn kho!")
                # Refresh lại danh sách
                self.load_master_data()
            except Exception as e:
                QMessageBox.warning(None, "Lỗi khi hủy", str(e))

    def handle_export_excel(self):
        if not self.selected_po_master or not self.current_po_details:
            return

        default_filename = f"PhieuNhap_{self.selected_po_master.code}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            None, "Xuất Excel Chi tiết Phiếu nhập", default_filename, "Excel Files (*.xlsx);;All Files (*)"
        )

        if file_path:
            if not file_path.endswith('.xlsx'): file_path += '.xlsx'
            success = PoHistoryExcelExporter.export_detail(file_path, self.selected_po_master, self.current_po_details)
            if success:
                QMessageBox.information(None, "Thành công", f"Đã xuất file Excel tại:\n{file_path}")
            else:
                QMessageBox.critical(None, "Lỗi", "Có lỗi xảy ra trong quá trình ghi file Excel. Vui lòng xem log.")