from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from app.modules.inventory.ui.generated.ui_purchase_order_confirm import Ui_PurchaseOrderConfirmDialog
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO


class PurchaseOrderConfirmController(QDialog):
    def __init__(self, dto: PurchaseOrderCreateDTO, supplier_name: str, raw_item_details: list):
        super().__init__()
        self.ui = Ui_PurchaseOrderConfirmDialog()
        self.ui.setupUi(self)

        self.dto = dto
        self.supplier_name = supplier_name
        self.raw_item_details = raw_item_details  # Chứa Tên SP, Mã SKU, ĐVT dạng chữ để hiển thị

        self.setup_ui()
        self.populate_data()
        self.bind_events()

    def setup_ui(self):
        # Format bảng cho đẹp
        header = self.ui.tbl_items.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Cột Tên SP giãn ra
        self.ui.tbl_items.verticalHeader().setVisible(False)

    def bind_events(self):
        # Nếu bấm Confirm -> Trả về QDialog.DialogCode.Accepted
        self.ui.btn_confirm.clicked.connect(self.accept)
        # Nếu bấm Cancel -> Trả về QDialog.DialogCode.Rejected
        self.ui.btn_cancel.clicked.connect(self.reject)

    def populate_data(self):
        # Đổ dữ liệu Header
        self.ui.lbl_supplier_name.setText(self.supplier_name)
        self.ui.lbl_note.setText(self.dto.note if self.dto.note else "Không có ghi chú")

        # Đổ dữ liệu Bảng chi tiết
        self.ui.tbl_items.setRowCount(len(self.raw_item_details))
        total_amount = 0

        for i, item_detail in enumerate(self.raw_item_details):
            # item_detail là một dictionary chứa thông tin hiển thị được truyền từ màn hình chính sang
            sku = QTableWidgetItem(item_detail['sku'])
            sku.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            name = QTableWidgetItem(item_detail['name'])

            unit = QTableWidgetItem(item_detail['unit_name'])
            unit.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            qty = QTableWidgetItem(str(item_detail['qty']))
            qty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            price = QTableWidgetItem(f"{item_detail['price']:,.0f}")
            price.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            line_total = item_detail['qty'] * item_detail['price']
            total_amount += line_total

            total = QTableWidgetItem(f"{line_total:,.0f}")
            total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.ui.tbl_items.setItem(i, 0, sku)
            self.ui.tbl_items.setItem(i, 1, name)
            self.ui.tbl_items.setItem(i, 2, unit)
            self.ui.tbl_items.setItem(i, 3, qty)
            self.ui.tbl_items.setItem(i, 4, price)
            self.ui.tbl_items.setItem(i, 5, total)

        # Đổ Tổng tiền
        self.ui.lbl_total_amount.setText(f"{total_amount:,.0f} VNĐ")