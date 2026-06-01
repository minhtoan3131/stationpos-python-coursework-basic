import traceback

from PyQt6.QtWidgets import (
    QWidget,
    QTableWidgetItem,
    QMessageBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from app.modules.product.ui.controllers.quick_price_controller import QuickPriceDialogController
from app.modules.product.ui.generated.ui_product_management import Ui_ProductManagementWidget
from app.modules.product.dtos.product_filter_dto import ProductFilterDTO
from app.modules.product.dtos.product_delete_dto import ProductDeleteDTO
from app.core.exceptions.validation_exception import ValidationException
from app.modules.product.ui.controllers.product_form_controller import ProductFormController

from app.modules.product.services.product_service import ProductService
from app.modules.product.services.category_service import CategoryService
from app.modules.product.services.supplier_service import SupplierService
from app.modules.product.services.unit_service import UnitService
from app.modules.product.ultils.product_margin_calculator import ProductMarginCalculator


# =========================================================================
# LỚP TIỆN ÍCH CHUYÊN BIỆT: ÉP BUỘC SẮP XẾP THEO GIÁ TRỊ SỐ THỰC GỐC
# =========================================================================
class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value: float, display_text: str):
        super().__init__(display_text)
        self.value = value

    def __lt__(self, other):
        # Chặn phép so sánh của Qt để so sánh 2 số thực thay vì 2 chuỗi text
        if isinstance(other, NumericTableWidgetItem):
            return self.value < other.value
        return super().__lt__(other)


class ProductManagementController(QWidget):

    def __init__(self,
                 product_service: ProductService,
                 category_service: CategoryService,
                 supplier_service: SupplierService,
                 unit_service: UnitService):
        super().__init__()

        self.ui = Ui_ProductManagementWidget()
        self.ui.setupUi(self)
        self.product_service = product_service
        self.category_service = category_service
        self.supplier_service = supplier_service
        self.unit_service = unit_service
        self.ui.tbl_products.setColumnHidden(0, True)

        # Setup các cột cho hài hòa
        header = self.ui.tbl_products.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Ép riêng cột "Tên sản phẩm" (Cột index 2) ở chế độ STRETCH - rộng nhất
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Phân bổ kích thước khởi tạo ban đầu cho các cột còn lại
        self.ui.tbl_products.setColumnWidth(1, 100)  # SKU
        self.ui.tbl_products.setColumnWidth(3, 110)  # Danh mục
        self.ui.tbl_products.setColumnWidth(4, 130)  # Nhà cung cấp
        self.ui.tbl_products.setColumnWidth(5, 100)  # Tồn kho
        self.ui.tbl_products.setColumnWidth(6, 110)  # Giá vốn MAC
        self.ui.tbl_products.setColumnWidth(7, 110)  # Giá bán lẻ
        self.ui.tbl_products.setColumnWidth(8, 110)  # Giá bán sỉ
        self.ui.tbl_products.setColumnWidth(9, 100)  # Biên LN lẻ
        self.ui.tbl_products.setColumnWidth(10, 150) # Barcode

        self.load_products()
        self.bind_events()

    def bind_events(self):
        self.ui.btn_search_products.clicked.connect(self.search_products)
        self.ui.btn_refresh_products.clicked.connect(self.load_products)
        self.ui.btn_delete_product.clicked.connect(self.delete_product)
        self.ui.btn_create_product.clicked.connect(self.open_create_dialog)
        self.ui.btn_update_product.clicked.connect(self.open_update_dialog)

        self.ui.txt_search_keyword.returnPressed.connect(self.search_products)
        self.ui.tbl_products.cellDoubleClicked.connect(self.open_update_dialog)
        self.ui.btn_adjust_price.clicked.connect(self.open_price_dialog)

    def load_products(self):
        try:
            products = self.product_service.get_product_list()
            self.populate_product_table(products)
            self.ui.txt_search_keyword.clear()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống", f"Không thể tải danh sách sản phẩm:\n{str(e)}")

    def populate_product_table(self, products):
        # BẮT BUỘC: Khóa tính năng sorting trước khi cấu hình dòng để chống giật lag và lỗi lệch chỉ số dòng mid-loop
        self.ui.tbl_products.setSortingEnabled(False)

        self.ui.tbl_products.setRowCount(0)
        self.ui.tbl_products.setRowCount(len(products))

        for row_index, product in enumerate(products):
            # Cột 0: ID (Ẩn ngầm - Dùng số nguyên để sắp xếp thứ tự ID chuẩn xác)
            id_val = int(product.id) if product.id else 0
            self.ui.tbl_products.setItem(row_index, 0, NumericTableWidgetItem(id_val, str(product.id)))

            # Cột 1, 2, 3, 4: Điền thông tin SKU, Tên, Danh mục, Nhà cung cấp (Văn bản thuần)
            self.ui.tbl_products.setItem(row_index, 1, QTableWidgetItem(product.sku))
            self.ui.tbl_products.setItem(row_index, 2, QTableWidgetItem(product.name))
            self.ui.tbl_products.setItem(row_index, 3, QTableWidgetItem(product.category_name))
            self.ui.tbl_products.setItem(row_index, 4, QTableWidgetItem(product.supplier_name or "---"))

            # Cột 5: Tồn kho hiện tại (Dùng NumericTableWidgetItem để trích xuất số lượng gốc phục vụ sort)
            stock_qty_val = float(product.stock_qty) if product.stock_qty else 0.0
            stock_display = f"{product.stock_qty:,} {product.unit_name}"
            stock_item = NumericTableWidgetItem(stock_qty_val, stock_display)
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_products.setItem(row_index, 5, stock_item)

            # Cột 6: Giá vốn trung bình MAC (Dùng NumericTableWidgetItem mới)
            cost_val = float(product.cost_price) if product.cost_price else 0.0
            cost_item = NumericTableWidgetItem(cost_val, f"{cost_val:,.0f}")
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cost_item.setForeground(QColor("#4b5563"))  # Đặt màu xám thanh lịch cho trường dữ liệu nội bộ
            self.ui.tbl_products.setItem(row_index, 6, cost_item)

            # Cột 7: Giá bán lẻ (Dùng NumericTableWidgetItem mới)
            retail_val = float(product.retail_price) if product.retail_price else 0.0
            retail_item = NumericTableWidgetItem(retail_val, f"{retail_val:,.0f}")
            retail_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # ột 8: Giá bán sỉ (Dùng NumericTableWidgetItem mới)
            wholesale_val = float(product.wholesale_price) if product.wholesale_price else 0.0
            wholesale_item = NumericTableWidgetItem(wholesale_val, f"{wholesale_val:,.0f}" if wholesale_val > 0 else "---")
            wholesale_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_products.setItem(row_index, 8, wholesale_item)

            # Cột 9: Biên lợi nhuận lẻ (%) (Gọi bộ tính toán và bao bọc bởi NumericTableWidgetItem)
            margin_percent, margin_text, hex_color = ProductMarginCalculator.calculate_margin_and_status(
                retail_price=product.retail_price,
                cost_price=product.cost_price
            )

            margin_item = NumericTableWidgetItem(float(margin_percent), margin_text)
            margin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Giữ nguyên hệ thống bôi màu cảnh báo và in đậm chữ theo mã Hex trả về
            color = QColor(hex_color)
            margin_item.setForeground(color)

            if hex_color in ["#ef4444", "#d97706"]:  # Nếu LỖ hoặc HÒA vốn thì kích hoạt font in đậm chữ
                font_bold = retail_item.font()
                font_bold.setBold(True)
                margin_item.setFont(font_bold)

                if hex_color == "#ef4444":  # Chỉ bôi đỏ ô Giá bán lẻ khi thực sự bị LỖ vốn nguy hiểm
                    retail_item.setForeground(color)
                    retail_item.setFont(font_bold)

            self.ui.tbl_products.setItem(row_index, 7, retail_item)
            self.ui.tbl_products.setItem(row_index, 9, margin_item)

            # Cột 10: Barcode (Văn bản thuần)
            self.ui.tbl_products.setItem(row_index, 10, QTableWidgetItem(product.barcode or ""))

        self.ui.lbl_total_products.setText(f"Tổng cộng: {len(products):,} sản phẩm")

        # Mở khóa kích hoạt lại tính năng sorting sau khi toàn bộ dữ liệu đã được nạp
        self.ui.tbl_products.setSortingEnabled(True)
        self.ui.tbl_products.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def search_products(self):
        try:
            keyword = self.ui.txt_search_keyword.text().strip()
            filter_dto = ProductFilterDTO(keyword=keyword, category_id=None, supplier_id=None, is_active=True)
            products = self.product_service.search_products(filter_dto)
            self.populate_product_table(products)
        except ValidationException as ve:
            QMessageBox.warning(self, "Cảnh báo dữ liệu", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi tìm kiếm", f"Đã xảy ra lỗi:\n{str(e)}")

    def delete_product(self):
        selected_row = self.ui.tbl_products.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, "Hướng dẫn", "Vui lòng click chọn một sản phẩm trong bảng trước khi xóa.")
            return

        product_id = int(self.ui.tbl_products.item(selected_row, 0).text())
        product_name = self.ui.tbl_products.item(selected_row, 2).text()

        confirm = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa sản phẩm:\n[{product_name}]?\n\nLưu ý: Dữ liệu sẽ được ẩn đi để đảm bảo tính toàn vẹn của các hóa đơn cũ.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes: return

        try:
            dto = ProductDeleteDTO(product_id=product_id)
            self.product_service.delete_product(dto)
            QMessageBox.information(self, "Thành công", f"Đã xóa thành công sản phẩm: {product_name}")
            self.load_products()
        except ValidationException as ve:
            QMessageBox.warning(self, "Không thể xóa", str(ve))
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống", f"Lỗi không xác định khi xóa:\n{str(e)}")

    def open_create_dialog(self):
        dialog = ProductFormController(
            product_service=self.product_service, category_service=self.category_service,
            supplier_service=self.supplier_service, unit_service=self.unit_service
        )
        if dialog.exec(): self.load_products()

    def open_update_dialog(self):
        selected_row = self.ui.tbl_products.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, "Hướng dẫn", "Vui lòng click chọn một sản phẩm trong bảng để chỉnh sửa.")
            return

        product_id = int(self.ui.tbl_products.item(selected_row, 0).text())
        dialog = ProductFormController(
            product_service=self.product_service, category_service=self.category_service,
            supplier_service=self.supplier_service, unit_service=self.unit_service, product_id=product_id
        )
        if dialog.exec(): self.load_products()

    def open_price_dialog(self):
        selected_row = self.ui.tbl_products.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, "Hướng dẫn", "Vui lòng chọn một dòng sản phẩm trên bảng để điều chỉnh giá.")
            return

        product_id = int(self.ui.tbl_products.item(selected_row, 0).text())

        try:
            product_detail = self.product_service.get_product_by_id(product_id)

            # Đọc live thông tin cấu hình từ DTO gốc để đảm bảo đồng bộ hệ quy chiếu ĐVT sỉ lẻ
            if product_detail.conversion_unit_name and product_detail.conversion_ratio:
                conv_display = f"{product_detail.conversion_unit_name} ({int(product_detail.conversion_ratio)} {product_detail.base_unit_name})"
            else:
                conv_display = "---"

            product_ratio = float(product_detail.conversion_ratio) if product_detail.conversion_ratio else 1.0
            dialog = QuickPriceDialogController(
                product_id=product_id, sku=product_detail.sku, name=product_detail.name,
                base_unit=product_detail.base_unit_name, conv_display=conv_display, ratio=product_ratio,
                mac_price=float(product_detail.cost_price), retail_price=float(product_detail.retail_price),
                wholesale_price=float(product_detail.wholesale_price) if product_detail.wholesale_price else 0.0,
                product_service=self.product_service
            )

            if dialog.exec(): self.load_products()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể tải thông tin sản phẩm:\n{str(e)}")