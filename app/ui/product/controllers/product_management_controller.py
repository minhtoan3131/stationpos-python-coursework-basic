from PyQt6.QtWidgets import (
    QWidget,
    QTableWidgetItem,
    QMessageBox
)
from PyQt6.QtCore import Qt

from app.ui.product.generated.ui_product_management import Ui_ProductManagementWidget
from app.modules.product.dtos.product_filter_dto import ProductFilterDTO
from app.modules.product.dtos.product_delete_dto import ProductDeleteDTO
from app.core.exceptions.validation_exception import ValidationException
from app.ui.product.controllers.product_form_controller import ProductFormController

from app.modules.product.services.product_service import ProductService
from app.modules.product.services.category_service import CategoryService
from app.modules.product.services.supplier_service import SupplierService
from app.modules.product.services.unit_service import UnitService


class ProductManagementController(QWidget):

    def __init__(self,
                 product_service: ProductService,
                 category_service: CategoryService,
                 supplier_service: SupplierService,
                 unit_service: UnitService):
        super().__init__()

        self.ui = Ui_ProductManagementWidget()
        self.ui.setupUi(self)
        self.ui.tbl_products.setColumnHidden(0, True)

        # Nhận service từ bên ngoài truyền vào
        self.product_service = product_service
        self.category_service = category_service
        self.supplier_service = supplier_service
        self.unit_service = unit_service

        self.load_products()

        self.bind_events()

    # =========================
    # BIND EVENTS
    # =========================

    def bind_events(self):
        self.ui.btn_search_products.clicked.connect(self.search_products)
        self.ui.btn_refresh_products.clicked.connect(self.load_products)
        self.ui.btn_delete_product.clicked.connect(self.delete_product)
        self.ui.btn_create_product.clicked.connect(self.open_create_dialog)
        self.ui.btn_update_product.clicked.connect(self.open_update_dialog)

        # Nhấn Enter ở ô tìm kiếm thì tự chạy hàm search
        self.ui.txt_search_keyword.returnPressed.connect(self.search_products)
        # Click đúp vào dòng nào thì tự động mở Form Sửa (Xem chi tiết) dòng đó
        self.ui.tbl_products.cellDoubleClicked.connect(self.open_update_dialog)

    def load_products(self):
        try:
            products = self.product_service.get_product_list()
            self.populate_product_table(products)
            # Clear text tìm kiếm khi bấm làm mới
            self.ui.txt_search_keyword.clear()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi hệ thống", f"Không thể tải danh sách sản phẩm:\n{str(e)}")

    def populate_product_table(self, products):
        self.ui.tbl_products.setRowCount(0)
        self.ui.tbl_products.setRowCount(len(products))

        for row_index, product in enumerate(products):
            # Cột 0: ID (Ẩn)
            self.ui.tbl_products.setItem(row_index, 0, QTableWidgetItem(str(product.id)))

            # Cột 1, 2, 3: SKU, Tên, Danh mục
            self.ui.tbl_products.setItem(row_index, 1, QTableWidgetItem(product.sku))
            self.ui.tbl_products.setItem(row_index, 2, QTableWidgetItem(product.name))
            self.ui.tbl_products.setItem(row_index, 3, QTableWidgetItem(product.category_name))

            # Cột 4: ĐVT Lẻ (Base Unit)
            self.ui.tbl_products.setItem(row_index, 4, QTableWidgetItem(product.unit_name))

            # Cột 5: Giá Lẻ
            retail_item = QTableWidgetItem(f"{float(product.retail_price):,.0f}")
            retail_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_products.setItem(row_index, 5, retail_item)

            # Cột 6: ĐVT Sỉ (Gộp thông minh)
            if product.conversion_unit_name and product.conversion_ratio:
                # Ép kiểu thẳng về số nguyên để loại bỏ phần thập phân
                ratio_display = int(product.conversion_ratio)
                conv_display = f"{product.conversion_unit_name} ({ratio_display} {product.unit_name})"
            else:
                conv_display = "---"

            self.ui.tbl_products.setItem(row_index, 6, QTableWidgetItem(conv_display))

            # Cột 7: Giá Sỉ
            wholesale_val = float(product.wholesale_price) if product.wholesale_price else 0
            wholesale_item = QTableWidgetItem(f"{wholesale_val:,.0f}" if wholesale_val > 0 else "---")
            wholesale_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.ui.tbl_products.setItem(row_index, 7, wholesale_item)

            # Cột 8: Barcode
            self.ui.tbl_products.setItem(row_index, 8, QTableWidgetItem(product.barcode or ""))
            self.ui.lbl_total_products.setText(f"Tổng cộng: {len(products):,} sản phẩm")

    def search_products(self):
        try:
            keyword = self.ui.txt_search_keyword.text().strip()

            filter_dto = ProductFilterDTO(
                keyword=keyword,
                category_id=None,
                supplier_id=None,
                is_active=True
            )

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
            self,
            "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa sản phẩm:\n[{product_name}]?\n\nLưu ý: Dữ liệu sẽ được ẩn đi để đảm bảo tính toàn vẹn của các hóa đơn cũ.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            dto = ProductDeleteDTO(product_id=product_id)
            self.product_service.delete_product(dto)

            QMessageBox.information(self, "Thành công", f"Đã xóa thành công sản phẩm: {product_name}")
            self.load_products()

        except ValidationException as ve:
            QMessageBox.warning(self, "Không thể xóa", str(ve))

        # Bắt các lỗi hệ thống (Cơ sở dữ liệu sập, mất kết nối mạng...)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi hệ thống", f"Lỗi không xác định khi xóa:\n{str(e)}")

    # =========================
    # DIALOGS (CREATE / UPDATE)
    # =========================

    def open_create_dialog(self):
        dialog = ProductFormController(
            product_service=self.product_service,
            category_service=self.category_service,
            supplier_service=self.supplier_service,
            unit_service=self.unit_service
        )

        # Mở dialog dưới dạng Modal, chờ người dùng đóng lại mới chạy tiếp
        result = dialog.exec()
        if result:
            self.load_products()

    def open_update_dialog(self):
        selected_row = self.ui.tbl_products.currentRow()

        if selected_row < 0:
            QMessageBox.information(self, "Hướng dẫn", "Vui lòng click chọn một sản phẩm trong bảng để chỉnh sửa.")
            return

        product_id = int(self.ui.tbl_products.item(selected_row, 0).text())

        dialog = ProductFormController(
            product_service=self.product_service,
            category_service=self.category_service,
            supplier_service=self.supplier_service,
            unit_service=self.unit_service,
            product_id=product_id
        )

        result = dialog.exec()

        if result:
            self.load_products()