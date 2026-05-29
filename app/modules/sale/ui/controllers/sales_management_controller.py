import traceback
from decimal import Decimal
from PyQt6.QtWidgets import (
    QWidget, QHeaderView, QTableWidgetItem, QMessageBox,
    QPushButton, QAbstractItemView, QDialog, QSpinBox
)
from PyQt6.QtCore import Qt

from app.modules.sale.services.invoice_history_service import InvoiceHistoryService
from app.modules.sale.ui.controllers.invoice_history_controller import InvoiceHistoryController
from app.modules.sale.ui.generated.ui_sales_management import Ui_SalesManagementWidget
from app.modules.sale.ui.controllers.checkout_dialog_controller import CheckoutDialogController

from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.product.services.product_service import ProductService
from app.modules.sale.services.sale_service import SaleService

from app.modules.sale.dtos.sale_dto import CheckoutDTO, CartItemDTO
from app.modules.setting.dtos.store_config_dto import StoreConfigDTO
from app.modules.setting.services.store_config_service import StoreConfigService


class SalesManagementController(QWidget):
    def __init__(self,
                 inventory_service: InventoryService,
                 product_service: ProductService,
                 sale_service: SaleService,
                 invoice_history_service: InvoiceHistoryService,
                 store_config_service: StoreConfigService):
        super().__init__()
        self.ui = Ui_SalesManagementWidget()
        self.ui.setupUi(self)

        self.inventory_service = inventory_service
        self.product_service = product_service
        self.sale_service = sale_service
        self.invoice_history_service = invoice_history_service
        self.store_config_service = store_config_service

        # Dictionary lưu trữ dữ liệu ngầm cho mỗi dòng trên bảng Danh sách sản phẩm
        self.raw_sales_data = {}

        self.setup_ui_custom()
        self.bind_events()

        self.invoice_history_controller = InvoiceHistoryController(
            self.ui,
            self.invoice_history_service
        )

        # Load dữ liệu bảng bên trái ngay khi mở
        self.refresh_product_list()

    def setup_ui_custom(self):
        # Bảng bên trái (Danh sách Sản phẩm)
        self.ui.tbl_products_sales.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header_left = self.ui.tbl_products_sales.horizontalHeader()
        header_left.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header_left.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Bảng bên phải (Giỏ hàng)
        header_right = self.ui.tbl_cart.horizontalHeader()
        header_right.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_right.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self.ui.tbl_cart.setColumnWidth(2, 80)
        self.ui.tbl_cart.setColumnWidth(3, 85)
        self.ui.tbl_cart.setColumnWidth(6, 60)

    def bind_events(self):
        self.ui.btn_search.clicked.connect(self.handle_search)
        self.ui.txt_search_sales.returnPressed.connect(self.handle_search)
        self.ui.btn_add_to_cart.clicked.connect(self.add_selected_to_cart)
        self.ui.tbl_products_sales.cellDoubleClicked.connect(self.add_selected_to_cart)

        self.ui.btn_checkout.clicked.connect(self.handle_checkout)
        self.ui.btn_cancel_bill.clicked.connect(self.clear_cart)

        self.ui.tabWidget_sales.currentChanged.connect(self.handle_tab_changed)

    def handle_tab_changed(self, index):
        if index == 0:  # Trở về Tab Bán hàng
            self.ui.txt_search_sales.clear()
            self.refresh_product_list()  # Cập nhật tồn kho mới nhất
        elif index == 1:  # Chuyển sang Tab Lịch sử hóa đơn
            self.ui.txt_search_invoice.clear()
            self.invoice_history_controller.load_master_data()

    # ==========================================
    # LOGIC BÊN TRÁI: DANH SÁCH SẢN PHẨM
    # ==========================================
    def handle_search(self):
        keyword = self.ui.txt_search_sales.text().strip()
        self.refresh_product_list(keyword if keyword else None)

    def refresh_product_list(self, keyword: str = None):
        try:
            product_list = self.product_service.get_product_sale_list(keyword)
            self.display_product_table(product_list)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách sản phẩm: {str(e)}")

    def display_product_table(self, data_list):
        from app.modules.sale.utils.sale_calculator import SaleCalculator  # Import tiện ích tính toán

        self.ui.tbl_products_sales.setRowCount(0)
        self.raw_sales_data.clear()

        row_index = 0
        for p in data_list:
            # Lấy số lượng tồn kho cơ bản
            stock_qty = p.get('stock_qty') or 0
            base_cost = p.get('cost_price') or 0  # Lấy giá vốn cơ bản

            # DÒNG ĐƠN VỊ CƠ BẢN (Ví dụ: Cái)
            # --> CHỈ HIỂN THỊ NẾU TỒN KHO > 0
            if stock_qty > 0:
                self.ui.tbl_products_sales.insertRow(row_index)
                self.raw_sales_data[row_index] = {
                    'product_id': p['id'], 'sku': p['sku'], 'name': p['name'],
                    'unit_id': p['base_unit_id'], 'unit_name': p['base_unit_name'],
                    'price': p['retail_price'],
                    'cost_price': base_cost,
                }
                self.ui.tbl_products_sales.setItem(row_index, 0, QTableWidgetItem(p['sku']))
                self.ui.tbl_products_sales.setItem(row_index, 1, QTableWidgetItem(p['name']))
                self.ui.tbl_products_sales.setItem(row_index, 2, QTableWidgetItem(p['base_unit_name']))

                price_item = QTableWidgetItem(f"{float(p['retail_price']):,.0f}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.ui.tbl_products_sales.setItem(row_index, 3, price_item)

                # Hiển thị số lượng lẻ
                self.ui.tbl_products_sales.setItem(row_index, 4, QTableWidgetItem(str(stock_qty)))
                row_index += 1

            # 2. DÒNG ĐƠN VỊ QUY ĐỔI (Ví dụ: Hộp, Thùng)
            if p.get('conversion_unit_id') and p['conversion_unit_id'] != p['base_unit_id']:

                # Gọi Util để tính giá sỉ thực tế và số lượng quy đổi (Số hộp)
                actual_wholesale_price, actual_cost, conv_stock = SaleCalculator.calculate_conversion_details(
                    wholesale_price=p['wholesale_price'],
                    cost_price=base_cost,
                    base_stock=stock_qty,
                    ratio=p.get('ratio')
                )

                # --> CHỈ HIỂN THỊ NẾU CÒN ĐỦ HÀNG ĐỂ TẠO THÀNH ĐƠN VỊ SỈ (conv_stock > 0)
                if conv_stock > 0:
                    self.ui.tbl_products_sales.insertRow(row_index)

                    self.raw_sales_data[row_index] = {
                        'product_id': p['id'], 'sku': p['sku'], 'name': p['name'],
                        'unit_id': p['conversion_unit_id'], 'unit_name': p['conversion_unit_name'],
                        'price': actual_wholesale_price,
                        'cost_price': actual_cost,  # Lưu giá vốn sỉ đã nhân ratio
                    }

                    self.ui.tbl_products_sales.setItem(row_index, 0, QTableWidgetItem(p['sku']))
                    self.ui.tbl_products_sales.setItem(row_index, 1, QTableWidgetItem(p['name']))

                    unit_item = QTableWidgetItem(p['conversion_unit_name'])
                    unit_item.setForeground(Qt.GlobalColor.blue)
                    self.ui.tbl_products_sales.setItem(row_index, 2, unit_item)

                    price_item_si = QTableWidgetItem(f"{actual_wholesale_price:,.0f}")
                    price_item_si.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    price_item_si.setForeground(Qt.GlobalColor.blue)
                    self.ui.tbl_products_sales.setItem(row_index, 3, price_item_si)

                    self.ui.tbl_products_sales.setItem(row_index, 4, QTableWidgetItem(str(conv_stock)))
                    row_index += 1

    # ==========================================
    # LOGIC BÊN PHẢI: GIỎ HÀNG THU NGÂN
    # ==========================================
    def add_selected_to_cart(self):
        selected_row = self.ui.tbl_products_sales.currentRow()
        if selected_row < 0: return

        product_info = self.raw_sales_data[selected_row]

        for r in range(self.ui.tbl_cart.rowCount()):
            sku_in_cart = self.ui.tbl_cart.item(r, 0).text()
            unit_in_cart = self.ui.tbl_cart.item(r, 2).text()

            if sku_in_cart == product_info['sku'] and unit_in_cart == product_info['unit_name']:
                spin_qty = self.ui.tbl_cart.cellWidget(r, 3)
                if spin_qty:
                    spin_qty.setValue(spin_qty.value() + 1)
                return

        self.ui.tbl_cart.blockSignals(True)
        row_idx = self.ui.tbl_cart.rowCount()
        self.ui.tbl_cart.insertRow(row_idx)

        sku_item = QTableWidgetItem(product_info['sku'])
        sku_item.setData(Qt.ItemDataRole.UserRole, product_info['product_id'])
        self.ui.tbl_cart.setItem(row_idx, 0, sku_item)
        name_item = QTableWidgetItem(product_info['name'])
        name_item.setData(Qt.ItemDataRole.UserRole, product_info.get('cost_price', 0))
        self.ui.tbl_cart.setItem(row_idx, 1, name_item)

        unit_item = QTableWidgetItem(product_info['unit_name'])
        unit_item.setData(Qt.ItemDataRole.UserRole, product_info['unit_id'])
        self.ui.tbl_cart.setItem(row_idx, 2, unit_item)

        spin_qty = QSpinBox()
        spin_qty.setRange(1, 9999)
        spin_qty.setValue(1)
        spin_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin_qty.valueChanged.connect(self.calculate_total)
        self.ui.tbl_cart.setCellWidget(row_idx, 3, spin_qty)

        price_val = float(product_info['price']) if product_info['price'] else 0
        price_item = QTableWidgetItem(f"{price_val:,.0f}")
        price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        price_item.setFlags(price_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        self.ui.tbl_cart.setItem(row_idx, 4, price_item)

        self.ui.tbl_cart.setItem(row_idx, 5, QTableWidgetItem("0"))

        btn_del = QPushButton("Xóa")
        btn_del.setStyleSheet(
            "color: #ef4444; font-weight: bold; border: none; background-color: transparent; padding: 0px;")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(lambda checked, b=btn_del: self.handle_delete_row(b))
        self.ui.tbl_cart.setCellWidget(row_idx, 6, btn_del)

        self.ui.tbl_cart.blockSignals(False)
        self.calculate_total()

    def handle_delete_row(self, button):
        for row in range(self.ui.tbl_cart.rowCount()):
            if self.ui.tbl_cart.cellWidget(row, 6) == button:
                self.ui.tbl_cart.removeRow(row)
                self.calculate_total()
                break

    def calculate_total(self):
        self.ui.tbl_cart.blockSignals(True)
        total_bill = 0
        for r in range(self.ui.tbl_cart.rowCount()):
            try:
                spin_qty = self.ui.tbl_cart.cellWidget(r, 3)
                qty = spin_qty.value() if spin_qty else 0
                price = float(self.ui.tbl_cart.item(r, 4).text().replace(",", ""))
                line_total = qty * price

                total_item = QTableWidgetItem(f"{line_total:,.0f}")
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                total_item.setFlags(total_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.ui.tbl_cart.setItem(r, 5, total_item)

                total_bill += line_total
            except Exception:
                continue

        self.ui.lbl_total_bill.setText(f"{total_bill:,.0f} VND")
        self.ui.tbl_cart.blockSignals(False)

    def clear_cart(self):
        if self.ui.tbl_cart.rowCount() == 0: return
        confirm = QMessageBox.question(
            self, "Hủy hóa đơn", "Bạn có chắc chắn muốn xóa toàn bộ giỏ hàng?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.ui.tbl_cart.setRowCount(0)
            self.calculate_total()

    def handle_checkout(self):
        if self.ui.tbl_cart.rowCount() == 0:
            QMessageBox.warning(self, "Cảnh báo", "Giỏ hàng đang trống!")
            return

        cart_items = []
        total_amount = Decimal('0')

        # Đóng gói dữ liệu từ UI vào CartItemDTO
        for r in range(self.ui.tbl_cart.rowCount()):
            p_id = self.ui.tbl_cart.item(r, 0).data(Qt.ItemDataRole.UserRole)
            sku = self.ui.tbl_cart.item(r, 0).text()
            u_id = self.ui.tbl_cart.item(r, 2).data(Qt.ItemDataRole.UserRole)

            cost_price = Decimal(str(self.ui.tbl_cart.item(r, 1).data(Qt.ItemDataRole.UserRole)))

            spin_qty = self.ui.tbl_cart.cellWidget(r, 3)
            qty = spin_qty.value() if spin_qty else 0

            price = Decimal(self.ui.tbl_cart.item(r, 4).text().replace(",", ""))
            line_total = Decimal(self.ui.tbl_cart.item(r, 5).text().replace(",", ""))

            total_amount += line_total
            cart_items.append(CartItemDTO(
                product_id=p_id, sku=sku, name=self.ui.tbl_cart.item(r, 1).text(),
                unit_id=u_id, unit_name=self.ui.tbl_cart.item(r, 2).text(),
                quantity=qty, price=price, total=line_total,
                cost_price=cost_price
            ))

        # Khởi tạo CheckoutDTO gửi sang Dialog
        checkout_dto = CheckoutDTO(
            code="",  # Sẽ được sinh tự động ở màn hình Dialog
            total_amount=total_amount,
            discount=Decimal('0'),
            final_amount=total_amount,
            payment_method='CASH',
            cash_received=total_amount,
            items=cart_items
        )


        try:
            store_config = self.store_config_service.get_store_config()
        except Exception:
            # Fallback (Dự phòng) tạo DTO rỗng chứa data mặc định nếu xảy ra sự cố DB để không chặn luồng bán hàng
            store_config = StoreConfigDTO()

        dialog = CheckoutDialogController(checkout_dto, store_config, self)

        # Nếu thu ngân bấm Xác nhận thanh toán trên Dialog
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.is_confirmed:
            try:
                # GỌI XUỐNG TẦNG SERVICE ĐỂ XỬ LÝ DATABASE & KHO
                invoice_code = self.sale_service.process_checkout(checkout_dto)

                QMessageBox.information(self, "Thành công", f"Thanh toán thành công!\nMã HĐ: {invoice_code}")

                # Reset lại UI sau khi bán xong
                self.ui.tbl_cart.setRowCount(0)
                self.calculate_total()
                self.handle_search()  # Tải lại danh sách SP (cập nhật tồn kho mới nhất)

            except Exception as e:
                # Bắt lỗi Validation (ví dụ: Không đủ hàng) hoặc lỗi DB để báo cho Thu ngân
                QMessageBox.critical(self, "Lỗi thanh toán", str(e))