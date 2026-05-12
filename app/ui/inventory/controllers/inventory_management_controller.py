import datetime
import traceback

from PyQt6.QtWidgets import QWidget, QHeaderView, QTableWidgetItem, QComboBox, QMessageBox, QPushButton, \
    QAbstractItemView
from PyQt6.QtCore import Qt

from app.ui.inventory.generated.ui_inventory_management import Ui_InventoryManagementWidget
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.product.services.supplier_service import SupplierService
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, PurchaseOrderItemDTO
from app.core.exceptions.validation_exception import ValidationException


class InventoryManagementController(QWidget):
    def __init__(self, inventory_service: InventoryService, supplier_service: SupplierService):
        super().__init__()
        self.ui = Ui_InventoryManagementWidget()
        self.ui.setupUi(self)

        self.inventory_service = inventory_service
        self.supplier_service = supplier_service

        # Lưu trữ dữ liệu thô của danh sách tồn kho để dùng khi "Thêm vào phiếu"
        self.raw_inventory_data = {}

        self.setup_ui_custom()
        self.load_initial_data()
        self.bind_events()

        # Load dữ liệu bảng bên trái ngay khi mở
        self.refresh_inventory_list()

    def setup_ui_custom(self):
        """Cấu hình chi tiết cho 2 bảng side-by-side"""
        # 1. Bảng bên trái (Tồn kho)
        self.ui.tbl_inventory.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header_inv = self.ui.tbl_inventory.horizontalHeader()
        header_inv.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header_inv.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Tên SP giãn

        # 2. Bảng bên phải (Phiếu nhập)
        header_items = self.ui.tbl_items.horizontalHeader()
        header_items.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Tên SP giãn
        header_items.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # SKU vừa đủ
        self.ui.tbl_items.setColumnWidth(2, 100)  # Cột ĐVT

        # 3. Mặc định ngày nhập
        self.ui.txt_import_date.setText(datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))

    def load_initial_data(self):
        """Load dữ liệu cho các ComboBox"""
        self.ui.cbo_supplier.clear()
        self.ui.cbo_supplier.addItem("--- Chọn nhà cung cấp ---", 0)
        for sup in self.supplier_service.get_all_suppliers():
            self.ui.cbo_supplier.addItem(sup['name'], sup['id'])

    def bind_events(self):
        # Events bên trái (Inventory)
        self.ui.btn_search.clicked.connect(self.handle_search)
        self.ui.txt_search_inventory.returnPressed.connect(self.handle_search)
        self.ui.btn_import_action.clicked.connect(self.add_selected_to_cart)
        self.ui.tbl_inventory.cellDoubleClicked.connect(self.add_selected_to_cart)
        self.ui.btn_export_excel.clicked.connect(self.export_excel)

        # Events bên phải (Purchase Order)
        self.ui.btn_save_all.clicked.connect(self.handle_save_purchase)
        self.ui.btn_clear_all.clicked.connect(self.clear_purchase_cart)
        # Lắng nghe thay đổi giá trị trên bảng giỏ hàng để tính tiền
        self.ui.tbl_items.cellChanged.connect(self.calculate_cart_total)

    # ==========================================
    # LOGIC BÊN TRÁI: DANH SÁCH TỒN KHO
    # ==========================================

    def handle_search(self):
        keyword = self.ui.txt_search_inventory.text().strip()
        self.refresh_inventory_list(keyword if keyword else None)

    def refresh_inventory_list(self, keyword: str = None):
        try:
            inventory_data = self.inventory_service.get_inventory_list(keyword)
            self.display_inventory_table(inventory_data)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể tải tồn kho: {str(e)}")

    def display_inventory_table(self, data_list):
        self.ui.tbl_inventory.setRowCount(0)
        self.raw_inventory_data.clear()

        for row, item in enumerate(data_list):
            self.ui.tbl_inventory.insertRow(row)
            # Lưu lại ID và thông tin quy đổi để dùng sau
            self.raw_inventory_data[row] = item

            self.ui.tbl_inventory.setItem(row, 0, QTableWidgetItem(item.sku))
            self.ui.tbl_inventory.setItem(row, 1, QTableWidgetItem(item.product_name))

            qty_item = QTableWidgetItem(f"{item.total_base_quantity:,} {item.base_unit_name}")
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_inventory.setItem(row, 2, qty_item)

            self.ui.tbl_inventory.setItem(row, 3, QTableWidgetItem(item.conversion_quantity_str))

            min_stock = QTableWidgetItem(str(item.min_stock))
            min_stock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tbl_inventory.setItem(row, 4, min_stock)

            status_item = QTableWidgetItem(item.status)
            if item.total_base_quantity <= item.min_stock:
                status_item.setForeground(Qt.GlobalColor.red)
            else:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            self.ui.tbl_inventory.setItem(row, 5, status_item)

    # ==========================================
    # LOGIC BÊN PHẢI: GIỎ HÀNG NHẬP KHO
    # ==========================================

    def add_selected_to_cart(self):
        """Xử lý yêu cầu 2: Hiện đủ đơn vị sỉ khi thêm vào phiếu"""
        selected_row = self.ui.tbl_inventory.currentRow()
        if selected_row < 0: return

        product_info = self.raw_inventory_data[selected_row]

        # 1. Kiểm tra trùng trong giỏ
        for r in range(self.ui.tbl_items.rowCount()):
            if self.ui.tbl_items.item(r, 0).text() == product_info.sku:
                cur_qty = int(self.ui.tbl_items.item(r, 3).text())
                self.ui.tbl_items.item(r, 3).setText(str(cur_qty + 1))
                return

        # 2. Lấy thông tin đầy đủ của SP (bao gồm cả ĐVT quy đổi) từ Service
        # search_products_for_import trả về List[ProductDetailDTO]
        full_product_list = self.inventory_service.search_products_for_import(product_info.sku)
        if not full_product_list: return
        p = full_product_list[0]

        row_idx = self.ui.tbl_items.rowCount()
        self.ui.tbl_items.insertRow(row_idx)

        # SKU & Tên
        sku_item = QTableWidgetItem(p.sku)
        sku_item.setData(Qt.ItemDataRole.UserRole, p.id)
        self.ui.tbl_items.setItem(row_idx, 0, sku_item)
        self.ui.tbl_items.setItem(row_idx, 1, QTableWidgetItem(p.name))

        # FIX YÊU CẦU 2: Đổ dữ liệu vào ComboBox ĐVT
        cbo_unit = QComboBox()
        # Luôn có đơn vị cơ bản
        cbo_unit.addItem(p.base_unit_name, p.base_unit_id)

        # Nếu sản phẩm có đơn vị quy đổi (Sỉ), thêm vào ComboBox
        if p.conversion_unit_id and p.conversion_unit_id != p.base_unit_id:
            cbo_unit.addItem(p.conversion_unit_name, p.conversion_unit_id)
            # Tùy chọn: Tự động chọn đơn vị sỉ nếu đây là phiếu nhập hàng sỉ
            # cbo_unit.setCurrentIndex(1)

        cbo_unit.currentIndexChanged.connect(lambda: self.calculate_cart_total())
        self.ui.tbl_items.setCellWidget(row_idx, 2, cbo_unit)

        # SL & Giá
        self.ui.tbl_items.setItem(row_idx, 3, QTableWidgetItem("1"))
        cost_val = float(p.cost_price) if p.cost_price else 0
        self.ui.tbl_items.setItem(row_idx, 4, QTableWidgetItem(f"{cost_val:,.0f}"))

        # Nút xóa
        btn_del = QPushButton("Xóa")
        btn_del.setStyleSheet("color: #ef4444; font-weight: bold; border: none;")
        btn_del.clicked.connect(lambda checked, b=btn_del: self.handle_delete_row(b))
        self.ui.tbl_items.setCellWidget(row_idx, 6, btn_del)

        self.calculate_cart_total()

    def handle_delete_row(self, button):
        for row in range(self.ui.tbl_items.rowCount()):
            if self.ui.tbl_items.cellWidget(row, 6) == button:
                self.remove_cart_row(row)
                break

    def remove_cart_row(self, row):
        self.ui.tbl_items.removeRow(row)
        self.calculate_cart_total()

    def calculate_cart_total(self, *args):
        self.ui.tbl_items.blockSignals(True)
        total = 0
        for r in range(self.ui.tbl_items.rowCount()):
            try:
                qty_text = self.ui.tbl_items.item(r, 3).text()
                price_text = self.ui.tbl_items.item(r, 4).text().replace(",", "")

                line_total = int(qty_text) * float(price_text)
                self.ui.tbl_items.setItem(r, 5, QTableWidgetItem(f"{line_total:,.0f}"))
                total += line_total
            except:
                continue

        self.ui.lbl_total_value.setText(f"{total:,.0f} VND")
        self.ui.tbl_items.blockSignals(False)

    def clear_purchase_cart(self):
        self.ui.tbl_items.setRowCount(0)
        self.ui.txt_notes.clear()
        self.ui.cbo_supplier.setCurrentIndex(0)
        self.ui.txt_import_date.setText(datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.calculate_cart_total()

    def handle_save_purchase(self):
        supplier_id = self.ui.cbo_supplier.currentData()
        if supplier_id == 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn Nhà cung cấp!")
            return

        items = []
        for r in range(self.ui.tbl_items.rowCount()):
            cbo_unit = self.ui.tbl_items.cellWidget(r, 2)
            items.append(PurchaseOrderItemDTO(
                product_id=self.ui.tbl_items.item(r, 0).data(Qt.ItemDataRole.UserRole),
                unit_id=cbo_unit.currentData(),
                quantity=int(self.ui.tbl_items.item(r, 3).text()),
                unit_price=float(self.ui.tbl_items.item(r, 4).text().replace(",", ""))
            ))

        if not items:
            QMessageBox.warning(self, "Lỗi", "Giỏ hàng nhập đang trống!")
            return

        try:
            dto = PurchaseOrderCreateDTO(
                supplier_id=supplier_id,
                note=self.ui.txt_notes.text(),
                items=items
            )
            po_id = self.inventory_service.create_purchase_order(dto)
            QMessageBox.information(self, "Thành công", f"Đã nhập kho thành công! (Mã phiếu: {po_id})")

            # Sau khi lưu xong thì dọn sạch giỏ hàng và làm mới bảng tồn kho bên trái
            self.clear_purchase_cart()
            self.handle_search()

        except ValidationException as ve:
            QMessageBox.warning(self, "Cảnh báo", str(ve))
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống", str(e))

    def export_excel(self):
        QMessageBox.information(self, "Excel", "Tính năng đang được phát triển...")
