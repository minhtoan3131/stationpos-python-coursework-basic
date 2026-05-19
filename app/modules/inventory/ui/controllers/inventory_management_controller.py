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
        """Xử lý thêm vào phiếu và hiển thị SpinBox Số lượng"""
        selected_row = self.ui.tbl_inventory.currentRow()
        if selected_row < 0: return

        product_info = self.raw_inventory_data[selected_row]

        # 1. KIỂM TRA TRÙNG LẶP: Tăng giá trị SpinBox thay vì đổi text
        for r in range(self.ui.tbl_items.rowCount()):
            if self.ui.tbl_items.item(r, 0).text() == product_info.sku:
                spn = self.ui.tbl_items.cellWidget(r, 3)  # Lấy widget SpinBox ra
                spn.setValue(spn.value() + 1)  # Tăng thêm 1
                return

        # 2. THÊM DÒNG MỚI
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
        cbo_unit.currentIndexChanged.connect(lambda: self.calculate_cart_total())
        self.ui.tbl_items.setCellWidget(row_idx, 2, cbo_unit)

        # === TẠO SPINBOX SỐ LƯỢNG ===
        spn_qty = QSpinBox()
        spn_qty.setMinimum(1)  # Ít nhất là nhập 1
        spn_qty.setMaximum(999999)  # Giới hạn số lượng nhập tối đa
        spn_qty.setValue(1)  # Mặc định là 1
        spn_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sửa lỗi UX cuộn chuột (Giống bên Form Sản phẩm)
        spn_qty.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        spn_qty.wheelEvent = lambda event: event.ignore()

        # Bắt sự kiện: Cứ hễ người dùng bấm mũi tên tăng/giảm hoặc gõ phím -> Tính lại tiền
        spn_qty.valueChanged.connect(self.calculate_cart_total)
        self.ui.tbl_items.setCellWidget(row_idx, 3, spn_qty)
        # ======================================

        # Giá nhập
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
        self.cart.clear()

        for r in range(self.ui.tbl_items.rowCount()):
            sku_item = self.ui.tbl_items.item(r, 0)
            spn_qty = self.ui.tbl_items.cellWidget(r, 3)
            price_item = self.ui.tbl_items.item(r, 4)

            # Nếu dòng chưa được vẽ đầy đủ UI -> Bỏ qua an toàn
            if not sku_item or not spn_qty or not price_item:
                continue

            product_id = sku_item.data(Qt.ItemDataRole.UserRole)
            qty_val = spn_qty.value()
            price_text = price_item.text().replace(",", "")

            try:
                price_val = float(price_text)
                self.cart.update_item(product_id, qty_val, price_val)
                line_total = self.cart.items[product_id].line_total
                self.ui.tbl_items.setItem(r, 5, QTableWidgetItem(f"{line_total:,.0f}"))

            except ValueError:
                # Lỗi 1: Do dữ liệu sai định dạng (Expected Error) -> Bỏ qua nhẹ nhàng
                print(f"Cảnh báo: Dữ liệu giá không hợp lệ ở dòng {r}. Đang bỏ qua...")
                continue

            except Exception as e:
                # Lỗi 2: Vét các lỗi không lường trước (Unexpected Error) -> Ghi Log để dev sửa, không làm sập app
                print(f"Lỗi hệ thống không xác định tại dòng {r}: {str(e)}")
                traceback.print_exc()  # In chi tiết dòng code gây lỗi ra console/file log
                continue

        # CẬP NHẬT TỔNG TIỀN CUỐI CÙNG
        self.ui.lbl_total_value.setText(f"{self.cart.total_amount:,.0f} VND")

        self.ui.tbl_items.blockSignals(False)
    def clear_purchase_cart(self):
        self.ui.tbl_items.setRowCount(0)
        self.ui.txt_notes.clear()
        self.ui.cbo_supplier.setCurrentIndex(0)
        self.ui.txt_import_date.setText(datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.cart.clear()
        self.calculate_cart_total()

    def handle_save_purchase(self):
        supplier_id = self.ui.cbo_supplier.currentData()
        if supplier_id == 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn Nhà cung cấp!")
            return

        items = []
        raw_details_for_confirm = []  # Mảng lưu thông tin chữ để hiển thị lên bảng Confirm

        for r in range(self.ui.tbl_items.rowCount()):
            cbo_unit = self.ui.tbl_items.cellWidget(r, 2)
            spn_qty = self.ui.tbl_items.cellWidget(r, 3)

            qty_val = spn_qty.value()
            price_val = float(self.ui.tbl_items.item(r, 4).text().replace(",", ""))

            # Build DTO cho Service
            items.append(PurchaseOrderItemDTO(
                product_id=self.ui.tbl_items.item(r, 0).data(Qt.ItemDataRole.UserRole),
                unit_id=cbo_unit.currentData(),
                quantity=qty_val,
                unit_price=price_val
            ))

            # Build dữ liệu hiển thị cho Dialog Confirm
            raw_details_for_confirm.append({
                'sku': self.ui.tbl_items.item(r, 0).text(),
                'name': self.ui.tbl_items.item(r, 1).text(),
                'unit_name': cbo_unit.currentText(),
                'qty': qty_val,
                'price': price_val
            })

        if not items:
            QMessageBox.warning(self, "Lỗi", "Giỏ hàng nhập đang trống!")
            return

        try:
            dto = PurchaseOrderCreateDTO(
                supplier_id=supplier_id,
                note=self.ui.txt_notes.text(),
                items=items
            )

            # ==========================================
            # BƯỚC MỚI: HIỆN HỘP THOẠI XÁC NHẬN (CONFIRM)
            # ==========================================
            supplier_name = self.ui.cbo_supplier.currentText()
            confirm_dialog = PurchaseOrderConfirmController(dto, supplier_name, raw_details_for_confirm)

            # Nếu người dùng bấm "Quay lại" (Reject) -> Dừng tiến trình lưu
            if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
                return

                # ==========================================
            # NẾU ĐỒNG Ý: GỌI SERVICE ĐỂ LƯU VÀO DATABASE
            # ==========================================
            po_id = self.inventory_service.create_purchase_order(dto)
            QMessageBox.information(self, "Thành công", f"Đã nhập kho thành công! (Mã phiếu: {po_id})")

            # Dọn sạch giỏ hàng và làm mới bảng tồn kho
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