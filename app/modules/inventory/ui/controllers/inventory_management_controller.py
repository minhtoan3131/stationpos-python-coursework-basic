import datetime
import traceback

from PyQt6.QtWidgets import QWidget, QHeaderView, QTableWidgetItem, QComboBox, QMessageBox, QPushButton, \
    QAbstractItemView, QFileDialog, QSpinBox, QInputDialog, QDialog
from PyQt6.QtCore import Qt

from app.core.database.unit_of_work import UnitOfWork
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl
from app.modules.inventory.services.po_history_service import PurchaseOrderHistoryService
from app.modules.inventory.ui.controllers.inventory_history_controller import InventoryHistoryController
from app.modules.inventory.ui.controllers.purchase_order_confirm_controller import PurchaseOrderConfirmController
from app.modules.inventory.ui.generated.ui_inventory_management import Ui_InventoryManagementWidget
from app.modules.inventory.services.inventory_service import InventoryService
from app.modules.product.services.supplier_service import SupplierService
from app.modules.inventory.dtos.inventory_dto import PurchaseOrderCreateDTO, PurchaseOrderItemDTO
from app.core.exceptions.validation_exception import ValidationException
from app.modules.inventory.ui.models.purchase_cart import PurchaseCart


class InventoryManagementController(QWidget):
    def __init__(self,
                 inventory_service: InventoryService,
                 supplier_service: SupplierService,
                 po_history_service: PurchaseOrderHistoryService):
        super().__init__()
        self.cart = PurchaseCart()
        self.ui = Ui_InventoryManagementWidget()
        self.ui.setupUi(self)

        self.inventory_service = inventory_service
        self.supplier_service = supplier_service
        self.po_history_service = po_history_service

        # Lưu trữ dữ liệu thô của danh sách tồn kho để dùng khi "Thêm vào phiếu"
        self.raw_inventory_data = {}

        self.setup_ui_custom()
        self.load_initial_data()
        self.bind_events()

        # Khởi tạo Sub-Controller quản lý Tab Lịch sử
        self.history_controller = InventoryHistoryController(self.ui, self.po_history_service)

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
        self.ui.btn_add_supplier.clicked.connect(self.quick_add_supplier)

        # Events bên phải (Purchase Order)
        self.ui.btn_save_all.clicked.connect(self.handle_save_purchase)
        self.ui.btn_clear_all.clicked.connect(self.clear_purchase_cart)
        # Lắng nghe thay đổi giá trị trên bảng giỏ hàng để tính tiền
        self.ui.tbl_items.cellChanged.connect(self.calculate_cart_total)

        self.ui.tabWidget_inventory.currentChanged.connect(self.handle_tab_changed)

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

            if item.is_low_stock:
                status_item = QTableWidgetItem("Sắp hết hàng")
                status_item.setForeground(Qt.GlobalColor.red)
            else:
                status_item = QTableWidgetItem("Bình thường")
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            self.ui.tbl_inventory.setItem(row, 5, status_item)

    # ==========================================
    # LOGIC BÊN PHẢI: GIỎ HÀNG NHẬP KHO
    # ==========================================

    def add_selected_to_cart(self):
        """Xử lý thêm vào phiếu"""
        selected_row = self.ui.tbl_inventory.currentRow()
        if selected_row < 0: return

        product_info = self.raw_inventory_data[selected_row]

        # THÊM DÒNG MỚI
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

        # ĐVT (ComboBox)
        cbo_unit = QComboBox()
        cbo_unit.addItem(p.base_unit_name, p.base_unit_id)
        if p.conversion_unit_id and p.conversion_unit_id != p.base_unit_id:
            cbo_unit.addItem(p.conversion_unit_name, p.conversion_unit_id)

        # Đồng bộ tính lại tiền khi thay đổi ĐVT (đơn giá giữ nguyên theo thói quen gõ của user)
        cbo_unit.currentIndexChanged.connect(lambda: self.calculate_cart_total())
        self.ui.tbl_items.setCellWidget(row_idx, 2, cbo_unit)

        # SpinBox Số lượng
        spn_qty = QSpinBox()
        spn_qty.setMinimum(1)
        # Đặt hạn mức trần số lượng nhập kho trên 1 dòng là 100,000 (Chống tràn số)
        spn_qty.setMaximum(100000)
        spn_qty.setValue(1)
        spn_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spn_qty.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        spn_qty.wheelEvent = lambda event: event.ignore()
        spn_qty.valueChanged.connect(self.calculate_cart_total)
        self.ui.tbl_items.setCellWidget(row_idx, 3, spn_qty)

        # === ĐỂ TRỐNG GIÁ NHẬP KHÔNG TỰ ĐIỀN ===
        # Thay vì điền cost_val lịch sử, ta để chuỗi rỗng bắt buộc người dùng tự gõ giá thực tế
        price_item = QTableWidgetItem("")
        self.ui.tbl_items.setItem(row_idx, 4, price_item)

        # Thành tiền tạm thời để trống/0
        self.ui.tbl_items.setItem(row_idx, 5, QTableWidgetItem("0"))

        # Nút xóa dòng
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
        """
        Tính toán tổng tiền dòng và tổng tiền giỏ hàng.
        ĐÃ SỬA LỖI: Hỗ trợ tính cộng dồn lũy tiến khi một sản phẩm xuất hiện trên nhiều dòng (Sỉ & Lẻ).
        """
        self.ui.tbl_items.blockSignals(True)
        self.cart.clear()

        # 2. Tạo biến tạm để tích lũy tổng tiền toàn bộ giỏ hàng
        running_total_cart_amount = 0.0

        for r in range(self.ui.tbl_items.rowCount()):
            sku_item = self.ui.tbl_items.item(r, 0)
            spn_qty = self.ui.tbl_items.cellWidget(r, 3)
            price_item = self.ui.tbl_items.item(r, 4)

            if not sku_item or not spn_qty or not price_item:
                continue

            qty_val = spn_qty.value()
            price_text = price_item.text().strip().replace(",", "")

            # Nếu ô giá nhập trống, coi như thành tiền dòng này là 0đ để gõ tiếp
            if not price_text:
                self.ui.tbl_items.setItem(r, 5, QTableWidgetItem("0"))
                continue

            try:
                price_val = float(price_text)
                if price_val < 0:
                    self.ui.tbl_items.setItem(r, 5, QTableWidgetItem("0"))
                    continue

                # 3. Tính toán thành tiền trực tiếp của dòng hiện tại (Không qua object cart)
                line_total = qty_val * price_val
                self.ui.tbl_items.setItem(r, 5, QTableWidgetItem(f"{line_total:,.0f}"))

                # 4. Cộng dồn trực tiếp vào tổng tiền chung của cả giỏ hàng
                running_total_cart_amount += line_total

            except ValueError:
                self.ui.tbl_items.setItem(r, 5, QTableWidgetItem("0"))
                continue
            except Exception as e:
                print(f"Lỗi hệ thống không xác định tại dòng {r}: {str(e)}")
                continue

        # 5. Cập nhật con số tổng tiền chuẩn xác sau khi đã cộng dồn toàn bộ các dòng
        self.ui.lbl_total_value.setText(f"{running_total_cart_amount:,.0f} VND")

        self.ui.tbl_items.blockSignals(False)


    def clear_purchase_cart(self):
        self.ui.tbl_items.setRowCount(0)
        self.ui.txt_notes.clear()
        self.ui.cbo_supplier.setCurrentIndex(0)
        self.ui.txt_import_date.setText(datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.cart.clear()
        self.calculate_cart_total()

    def handle_save_purchase(self):
        """Xác nhận nhập kho - Truyền trực tiếp dữ liệu thô xuống Service để bảo toàn Decimal"""
        supplier_id = self.ui.cbo_supplier.currentData()
        if supplier_id == 0:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn Nhà cung cấp!")
            return

        if self.ui.tbl_items.rowCount() == 0:
            QMessageBox.warning(self, "Cảnh báo", "Giỏ hàng nhập hiện đang trống!")
            return

        items_dto = []
        raw_details_for_confirm = []

        # Quét qua từng dòng vật lý trên UI
        for r in range(self.ui.tbl_items.rowCount()):
            sku_item = self.ui.tbl_items.item(r, 0)
            prod_name = self.ui.tbl_items.item(r, 1).text()
            cbo_unit = self.ui.tbl_items.cellWidget(r, 2)
            spn_qty = self.ui.tbl_items.cellWidget(r, 3)
            price_item = self.ui.tbl_items.item(r, 4)

            if not sku_item or not spn_qty:
                continue

            product_id = sku_item.data(Qt.ItemDataRole.UserRole)
            sku_text = sku_item.text()
            qty_val = spn_qty.value()

            # Đọc chuỗi text trong ô giá gõ tay
            price_text = price_item.text().strip().replace(",", "") if price_item else ""

            if not price_text:
                QMessageBox.warning(
                    self,
                    "Dữ liệu không hợp lệ",
                    f"Mặt hàng [{sku_text}] - {prod_name} đang để trống giá!"
                )
                return

            try:
                price_val = float(price_text)
                if price_val <= 0:
                    raise ValueError
                # Khống chế đơn giá nhập của từng món không vượt quá 1 Tỷ VND
                MAX_PRICE_CEILING = 1000000000.0  # 1 Tỷ VND
                if price_val > MAX_PRICE_CEILING:
                    QMessageBox.warning(
                        self, "Dữ liệu vượt hạn mức",
                        f"Đơn giá nhập của mặt hàng [{sku_text}] vượt quá hạn mức tối đa cho phép (1 Tỷ VND)!\n"
                        f"Vui lòng kiểm tra lại số lượng đã nhập"
                    )
                    return
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Dữ liệu không hợp lệ",
                    f"Giá nhập mặt hàng [{sku_text}] phải > 0!"
                )
                return

            # Bê nguyên đại lượng thô từ UI (Hộp gõ sao giữ vậy) đút thẳng vào DTO gửi đi.
            items_dto.append(PurchaseOrderItemDTO(
                product_id=product_id,
                unit_id=cbo_unit.currentData(),  # Giữ nguyên ID đơn vị Sỉ (Hộp) người dùng chọn
                quantity=qty_val,               # Số lượng nguyên bản (Ví dụ: 3 Hộp)
                unit_price=price_val            # Đơn giá nguyên bản (Ví dụ: 100,000 VND)
            ))

            raw_details_for_confirm.append({
                'sku': sku_text, 'name': prod_name, 'unit_name': cbo_unit.currentText(),
                'qty': qty_val, 'price': price_val
            })

        # Đánh chặn tổng tiền toàn bộ phiếu nhập trước khi đẩy xuống DB
        # Ngưỡng khống chế an toàn là 50 Tỷ VND (Dưới ngưỡng 99 Tỷ của cấu trúc DECIMAL(15,4))
        total_po_amount = sum(item.quantity * item.unit_price for item in items_dto)
        MAX_FINANCIAL_CEILING = 50000000000.0  # 50 Tỷ VND

        if total_po_amount > MAX_FINANCIAL_CEILING:
            QMessageBox.critical(
                self, "Từ chối giao dịch",
                f"⚠️ <b>VƯỢT NGƯỠNG HẠN MỨC HỆ THỐNG:</b>\n\n"
                f"Tổng giá trị phiếu nhập kho hiện tại là: <b>{total_po_amount:,.0f} VND</b>.\n"
                f"Vui lòng tách nhỏ phiếu này thành các chứng từ nhập kho độc lập!"
            )
            return

        try:
            dto = PurchaseOrderCreateDTO(
                supplier_id=supplier_id,
                note=self.ui.txt_notes.text(),
                items=items_dto
            )

            # Hiện hộp thoại xác nhận tổng thể
            supplier_name = self.ui.cbo_supplier.currentText()
            confirm_dialog = PurchaseOrderConfirmController(dto, supplier_name, raw_details_for_confirm)
            if confirm_dialog.exec() != QDialog.DialogCode.Accepted: return

            # Gọi Service xử lý - Nhường toàn bộ quyền tính toán an toàn cho toán học Decimal
            po_id = self.inventory_service.create_purchase_order(dto)
            QMessageBox.information(self, "Thành công", f"Đã nhập kho thành công! (Mã phiếu: {po_id})")

            self.clear_purchase_cart()
            self.handle_search()

        except ValidationException as ve:
            QMessageBox.warning(self, "Cảnh báo", str(ve))
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống", str(e))

    def export_excel(self):
        """Xử lý sự kiện khi người dùng bấm nút Xuất File Báo Cáo"""

        # Tạo tên file mặc định có chứa ngày tháng hiện tại
        default_filename = f"BaoCaoTonKho_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        # Mở hộp thoại chọn nơi lưu file
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu báo cáo tồn kho",
            default_filename,
            "Excel Files (*.xlsx);;All Files (*)"
        )

        # Nếu người dùng bấm "Hủy" trong hộp thoại lưu file
        if not file_path:
            return

        # Gọi Service để tạo và ghi file Excel
        try:
            # Đảm bảo file có đuôi .xlsx
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'

            success = self.inventory_service.export_inventory_to_excel(file_path)

            if success:
                QMessageBox.information(self, "Thành công", f"Đã xuất báo cáo thành công tại:\n{file_path}")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống", f"Không thể xuất file Excel:\n{str(e)}")

    def quick_add_supplier(self):
        text, ok = QInputDialog.getText(self, "Thêm Nhà cung cấp", "Nhập tên nhà cung cấp mới:")
        if ok and text.strip():
            try:
                new_id = self.supplier_service.create_supplier(text.strip())

                # Cập nhật UI: Thêm vào combobox và chọn luôn NCC đó
                self.ui.cbo_supplier.addItem(text.strip(), new_id)
                self.ui.cbo_supplier.setCurrentIndex(self.ui.cbo_supplier.count() - 1)

            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Không thể thêm nhà cung cấp: {str(e)}")

    def showEvent(self, event):
        """Sự kiện kích hoạt mỗi khi màn hình này được hiển thị"""
        super().showEvent(event)
        # Làm mới danh sách nhà cung cấp trong ComboBox
        self.load_initial_data()
        # Làm mới luôn danh sách tồn kho (để cập nhật nếu có SP mới vừa thêm)
        self.refresh_inventory_list()

    def handle_tab_changed(self, index):
        """
        Xử lý sự kiện khi người dùng click chuyển đổi giữa các Tab.
        Tự động xóa trắng thanh tìm kiếm và làm mới dữ liệu mới nhất.
        """
        try:
            if index == 0:  # Người dùng click vào Tab Nhập kho & Tồn kho
                self.ui.txt_search_inventory.clear()
                self.refresh_inventory_list()

            elif index == 1:  # Người dùng click vào Tab Lịch sử Phiếu nhập
                self.ui.txt_search_po.clear()

                # Gọi thẳng hàm load dữ liệu của Sub-Controller để kéo dữ liệu mới nhất
                # Hàm này sẽ đọc trực tiếp ô txt_search_po vừa được xóa trống, trả về toàn bộ phiếu
                self.history_controller.load_master_data()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi chuyển Tab", f"Không thể làm mới dữ liệu: {str(e)}")