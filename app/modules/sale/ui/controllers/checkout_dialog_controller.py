from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QMessageBox, QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt
from datetime import datetime
from decimal import Decimal

from app.modules.sale.ui.generated.ui_checkout_confirmation import Ui_CheckoutDialog
from app.modules.sale.dtos.sale_dto import CheckoutDTO
from app.modules.sale.utils.sale_calculator import SaleCalculator
from app.modules.sale.utils.invoice_code_generator import InvoiceCodeGenerator
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO


class CheckoutDialogController(QDialog):
    def __init__(self, checkout_dto: CheckoutDTO, store_config: StoreConfigDTO = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_CheckoutDialog()
        self.ui.setupUi(self)

        self.checkout_dto = checkout_dto
        self.store_config = store_config if store_config else StoreConfigDTO()

        # Sinh mã hóa đơn ngay tại đây để hiển thị cho khách xem
        if not self.checkout_dto.code:
            self.checkout_dto.code = InvoiceCodeGenerator.generate()

        self.is_confirmed = False

        self.setup_ui_custom()
        self.populate_data()
        self.bind_events()

    def setup_ui_custom(self):
        # Cấu hình bảng hiển thị chi tiết hóa đơn
        header = self.ui.tbl_invoice_items.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.ui.tbl_invoice_items.verticalHeader().setVisible(False)
        self.ui.tbl_invoice_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def populate_data(self):
        # Điền thông tin hóa đơn
        self.ui.lbl_invoice_id.setText(f"Số HĐ: {self.checkout_dto.code}")
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.ui.lbl_date.setText(f"Ngày lập: {current_time}")

        store_text = f"Cửa hàng: {self.store_config.name}\nĐT: {self.store_config.phone} - ĐC: {self.store_config.address}"
        self.ui.lbl_store_info.setText(store_text)

        # Điền thông tin tổng tiền
        self.ui.lbl_grand_total.setText(f"{self.checkout_dto.final_amount:,.0f} VND")

        # Đổ dữ liệu từ DTO vào bảng
        self.ui.tbl_invoice_items.setRowCount(0)
        for row_idx, item in enumerate(self.checkout_dto.items):
            self.ui.tbl_invoice_items.insertRow(row_idx)

            # Cột 0: Tên SP
            name_item = QTableWidgetItem(item.name)
            self.ui.tbl_invoice_items.setItem(row_idx, 0, name_item)

            # Cột 1: ĐVT
            unit_item = QTableWidgetItem(item.unit_name)
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tbl_invoice_items.setItem(row_idx, 1, unit_item)

            # Cột 2: Số lượng
            qty_item = QTableWidgetItem(str(item.quantity))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tbl_invoice_items.setItem(row_idx, 2, qty_item)

            # Cột 3: Đơn giá
            price_item = QTableWidgetItem(f"{item.price:,.0f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_invoice_items.setItem(row_idx, 3, price_item)

            # Cột 4: Thành tiền
            total_item = QTableWidgetItem(f"{item.total:,.0f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_invoice_items.setItem(row_idx, 4, total_item)

        # Focus vào ô Tiền khách đưa (Phải ép về float vì QDoubleSpinBox chỉ nhận float)
        self.ui.spn_cash_received.setValue(float(self.checkout_dto.final_amount))
        self.ui.spn_cash_received.setFocus()
        self.ui.spn_cash_received.selectAll()
        self.calculate_change()

    def bind_events(self):
        self.ui.spn_cash_received.valueChanged.connect(self.calculate_change)
        self.ui.cbo_payment_method.currentIndexChanged.connect(self.handle_payment_method_change)

        self.ui.btn_confirm.clicked.connect(self.handle_confirm)
        self.ui.btn_back.clicked.connect(self.reject)

    def handle_payment_method_change(self, index):
        """Xử lý UI nếu chọn chuyển khoản thì khóa ô nhập tiền mặt."""
        if index == 1:  # Chuyển khoản / Quẹt thẻ
            self.ui.spn_cash_received.setValue(float(self.checkout_dto.final_amount))
            self.ui.spn_cash_received.setEnabled(False)
        else:  # Tiền mặt
            self.ui.spn_cash_received.setEnabled(True)
            self.ui.spn_cash_received.setFocus()
            self.ui.spn_cash_received.selectAll()

    def calculate_change(self):
        # Ép kiểu float -> string -> Decimal để tính toán chuẩn xác
        cash_received = Decimal(str(self.ui.spn_cash_received.value()))

        # Gọi Utils tính toán
        change_due = SaleCalculator.calculate_change(cash_received, self.checkout_dto.final_amount)

        if change_due < 0 and self.ui.cbo_payment_method.currentIndex() == 0:
            self.ui.lbl_change_due.setText("Khách đưa chưa đủ!")
            self.ui.lbl_change_due.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: 900;")
        else:
            self.ui.lbl_change_due.setText(f"{change_due:,.0f} VND")
            self.ui.lbl_change_due.setStyleSheet("color: #10b981; font-size: 22px; font-weight: 900;")

    def handle_confirm(self):
        payment_method = 'CASH' if self.ui.cbo_payment_method.currentIndex() == 0 else 'TRANSFER'

        # Ép kiểu sang Decimal
        cash_received = Decimal(str(self.ui.spn_cash_received.value()))

        if payment_method == 'CASH' and cash_received < self.checkout_dto.final_amount:
            QMessageBox.warning(self, "Cảnh báo", "Số tiền khách đưa chưa đủ để thanh toán hóa đơn này!")
            self.ui.spn_cash_received.setFocus()
            return

        # Cập nhật thông tin thanh toán cuối cùng vào DTO
        self.checkout_dto.payment_method = payment_method
        self.checkout_dto.cash_received = cash_received

        # Xác nhận thành công, trả về tín hiệu cho màn hình cha
        self.is_confirmed = True
        self.accept()