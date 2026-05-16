from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt

from app.modules.product.ui.generated.ui_product_form import Ui_ProductFormDialog
from app.modules.product.dtos.product_create_dto import ProductCreateDTO
from app.modules.product.dtos.product_update_dto import ProductUpdateDTO
from app.core.exceptions.validation_exception import ValidationException

# Import CÁC INTERFACE (Không import Impl)
from app.modules.product.services.product_service import ProductService
from app.modules.product.services.category_service import CategoryService
from app.modules.product.services.supplier_service import SupplierService
from app.modules.product.services.unit_service import UnitService


class ProductFormController(QDialog):
    def __init__(self,
                 product_service: ProductService,
                 category_service: CategoryService,
                 supplier_service: SupplierService,
                 unit_service: UnitService,
                 product_id=None):

        super().__init__()
        self.ui = Ui_ProductFormDialog()
        self.ui.setupUi(self)

        self.product_service = product_service
        self.category_service = category_service
        self.supplier_service = supplier_service
        self.unit_service = unit_service

        self.product_id = product_id

        self.format_number_inputs()
        self.load_comboboxes()
        self.disable_scroll_hijacking()  # FIX LỖI CUỘN CHUỘT

        # Xử lý phân nhánh: TẠO MỚI hay CẬP NHẬT
        if self.product_id is not None:
            self.setup_update_mode()
        else:
            self.setup_create_mode()

        self.bind_events()

    # =========================
    # BIND EVENTS
    # =========================
    def bind_events(self):
        self.ui.btn_save.clicked.connect(self.save_product)
        self.ui.btn_cancel.clicked.connect(self.close)
        self.ui.btn_add_category.clicked.connect(self.quick_add_category)
        self.ui.btn_add_supplier.clicked.connect(self.quick_add_supplier)
        self.ui.btn_add_base_unit.clicked.connect(self.quick_add_unit)
        self.ui.btn_add_conversion_unit.clicked.connect(self.quick_add_unit)

    # =========================
    # LOAD DỮ LIỆU MẪU COMBOBOX
    # =========================
    def load_comboboxes(self):
        # Danh mục
        self.ui.cbo_category.clear()
        for cat in self.category_service.get_all_categories():
            self.ui.cbo_category.addItem(cat['name'], cat['id'])

        # Nhà cung cấp
        self.ui.cbo_supplier.clear()
        self.ui.cbo_supplier.addItem("--- Không chọn ---", 0)
        for sup in self.supplier_service.get_all_suppliers():
            self.ui.cbo_supplier.addItem(sup['name'], sup['id'])

        # Đơn vị tính (Dùng chung cho cả 2 ô)
        units = self.unit_service.get_all_units()

        self.ui.cbo_base_unit.clear()
        for u in units:
            self.ui.cbo_base_unit.addItem(u['name'], u['id'])

        self.ui.cbo_conversion_unit.clear()
        self.ui.cbo_conversion_unit.addItem("--- Không có ---", 0)
        for u in units:
            self.ui.cbo_conversion_unit.addItem(u['name'], u['id'])

    # =========================
    # SETUP CHẾ ĐỘ MÀN HÌNH
    # =========================
    def setup_create_mode(self):
        self.setWindowTitle("Thêm mới Sản phẩm")
        self.ui.lbl_main_title.setText("THÊM MỚI SẢN PHẨM")

    def setup_update_mode(self):
        self.setWindowTitle("Cập nhật Sản phẩm")
        self.ui.lbl_main_title.setText("CẬP NHẬT SẢN PHẨM")
        # Khóa SKU (Không cho phép đổi mã SP khi update)
        self.ui.txt_sku.setEnabled(False)
        self.load_product_detail()

    def load_product_detail(self):
        try:
            product = self.product_service.get_product_by_id(self.product_id)

            # Đổ dữ liệu Text
            self.ui.txt_sku.setText(product.sku)
            self.ui.txt_name.setText(product.name)
            self.ui.txt_barcode.setText(product.barcode or "")
            self.ui.txt_description.setPlainText(product.description or "")

            # Đổ dữ liệu Combobox
            self.ui.cbo_category.setCurrentIndex(self.ui.cbo_category.findData(product.category_id))
            self.ui.cbo_base_unit.setCurrentIndex(self.ui.cbo_base_unit.findData(product.base_unit_id))

            sup_idx = self.ui.cbo_supplier.findData(product.supplier_id) if product.supplier_id else 0
            self.ui.cbo_supplier.setCurrentIndex(sup_idx)

            # Đổ dữ liệu Giá và Tồn
            self.ui.spn_cost_price.setValue(float(product.cost_price))
            self.ui.spn_retail_price.setValue(float(product.retail_price))
            self.ui.spn_wholesale_price.setValue(float(product.wholesale_price) if product.wholesale_price else 0)
            self.ui.spn_min_stock.setValue(product.min_stock)

            # Đổ dữ liệu Đơn vị quy đổi
            if product.conversion_unit_id:
                conv_idx = self.ui.cbo_conversion_unit.findData(product.conversion_unit_id)
                self.ui.cbo_conversion_unit.setCurrentIndex(conv_idx)
                self.ui.spn_conversion_ratio.setValue(float(product.conversion_ratio))
            else:
                self.ui.cbo_conversion_unit.setCurrentIndex(0)
                self.ui.spn_conversion_ratio.setValue(0)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi tải dữ liệu", f"Không thể lấy thông tin sản phẩm:\n{str(e)}")
            self.close()

    # =========================
    # LƯU DỮ LIỆU
    # =========================
    def save_product(self):
        try:
            # Thu thập dữ liệu thô từ Form
            sku = self.ui.txt_sku.text().strip()
            name = self.ui.txt_name.text().strip()
            barcode = self.ui.txt_barcode.text().strip()
            description = self.ui.txt_description.toPlainText().strip()

            category_id = self.ui.cbo_category.currentData()
            base_unit_id = self.ui.cbo_base_unit.currentData()

            # Xử lý các Combobox tùy chọn (Nếu chọn data = 0 thì gán thành None)
            supplier_data = self.ui.cbo_supplier.currentData()
            supplier_id = supplier_data if supplier_data != 0 else None

            conv_unit_data = self.ui.cbo_conversion_unit.currentData()
            conversion_unit_id = conv_unit_data if conv_unit_data != 0 else None

            conversion_ratio = self.ui.spn_conversion_ratio.value() if conversion_unit_id else None

            # Xử lý logic theo chế độ Tạo mới / Cập nhật
            if self.product_id is None:
                # --- CHẾ ĐỘ TẠO MỚI ---
                dto = ProductCreateDTO(
                    sku=sku if sku else None,  # Validator sẽ tự tạo nếu None
                    name=name,
                    barcode=barcode if barcode else None,
                    category_id=category_id,
                    supplier_id=supplier_id,
                    base_unit_id=base_unit_id,
                    cost_price=self.ui.spn_cost_price.value(),
                    retail_price=self.ui.spn_retail_price.value(),
                    wholesale_price=self.ui.spn_wholesale_price.value(),
                    min_stock=self.ui.spn_min_stock.value(),
                    description=description if description else None,
                    conversion_unit_id=conversion_unit_id,
                    conversion_ratio=conversion_ratio
                )

                new_id = self.product_service.create_product(dto)
                QMessageBox.information(self, "Thành công", f"Đã lưu sản phẩm mới thành công!\n(ID hệ thống: {new_id})")

            else:
                # --- CHẾ ĐỘ CẬP NHẬT ---
                dto = ProductUpdateDTO(
                    product_id=self.product_id,
                    sku=sku,
                    name=name,
                    barcode=barcode if barcode else None,
                    category_id=category_id,
                    supplier_id=supplier_id,
                    base_unit_id=base_unit_id,
                    cost_price=self.ui.spn_cost_price.value(),
                    retail_price=self.ui.spn_retail_price.value(),
                    wholesale_price=self.ui.spn_wholesale_price.value(),
                    min_stock=self.ui.spn_min_stock.value(),
                    description=description if description else None,
                    conversion_unit_id=conversion_unit_id,
                    conversion_ratio=conversion_ratio,
                    is_active=True
                )

                self.product_service.update_product(dto)
                QMessageBox.information(self, "Thành công", "Cập nhật thông tin sản phẩm thành công!")

            # Đóng Form và gửi tín hiệu cho cửa sổ cha load lại bảng
            self.accept()

        except ValidationException as ve:
            # Lưới bắt lỗi xịn xò từ Tầng Core (Validator)
            QMessageBox.warning(self, "Cảnh báo dữ liệu", str(ve))
        except Exception as e:
            # Lỗi hệ thống ngoài ý muốn
            QMessageBox.critical(self, "Lỗi hệ thống", f"Đã xảy ra lỗi:\n{str(e)}")

    # =========================
    # FIX UX: TẮT CUỘN CHUỘT TRÊN Ô NHẬP LIỆU
    # =========================
    def disable_scroll_hijacking(self):
        """Ngăn chặn việc cuộn chuột làm thay đổi giá trị của SpinBox và ComboBox"""

        def ignore_wheel(event):
            event.ignore()  # Bỏ qua sự kiện cuộn, trả lại cho QScrollArea

        widgets = [
            self.ui.spn_cost_price, self.ui.spn_retail_price,
            self.ui.spn_wholesale_price, self.ui.spn_min_stock,
            self.ui.spn_conversion_ratio,
            self.ui.cbo_category, self.ui.cbo_supplier,
            self.ui.cbo_base_unit, self.ui.cbo_conversion_unit
        ]

        for widget in widgets:
            # Ghi đè hàm cuộn chuột mặc định
            widget.wheelEvent = ignore_wheel
            # Yêu cầu người dùng phải click chuột vào mới được gõ phím
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def format_number_inputs(self):
        """Xóa phần thập phân (.00) và tự động thêm dấu phẩy hàng nghìn"""
        spinboxes = [
            self.ui.spn_cost_price,
            self.ui.spn_retail_price,
            self.ui.spn_wholesale_price,
            self.ui.spn_conversion_ratio
        ]

        for spn in spinboxes:
            # Tắt số thập phân (ẩn đuôi .00)
            spn.setDecimals(0)
            # Bật dấu phẩy phân cách hàng nghìn (VD: 150,000)
            spn.setGroupSeparatorShown(True)

    # =========================
    # CÁC HÀM QUICK CREATE
    # =========================
    def quick_add_category(self):
        text, ok = QInputDialog.getText(self, "Thêm Danh mục", "Nhập tên danh mục mới:")
        if ok and text.strip():
            try:
                new_id = self.category_service.create_category(text)
                self.ui.cbo_category.addItem(text.strip(), new_id)
                self.ui.cbo_category.setCurrentIndex(self.ui.cbo_category.count() - 1)
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", str(e))

    def quick_add_supplier(self):
        text, ok = QInputDialog.getText(self, "Thêm Nhà cung cấp", "Nhập tên nhà cung cấp mới:")
        if ok and text.strip():
            try:
                new_id = self.supplier_service.create_supplier(text)
                self.ui.cbo_supplier.addItem(text.strip(), new_id)
                self.ui.cbo_supplier.setCurrentIndex(self.ui.cbo_supplier.count() - 1)
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", str(e))

    def quick_add_unit(self):
        text, ok = QInputDialog.getText(self, "Thêm Đơn vị tính", "Nhập tên đơn vị tính mới (VD: Cái, Hộp):")
        if ok and text.strip():
            try:
                new_id = self.unit_service.create_unit(text)
                # Thêm vào cả 2 combobox đơn vị
                self.ui.cbo_base_unit.addItem(text.strip(), new_id)
                self.ui.cbo_conversion_unit.addItem(text.strip(), new_id)

                # Tự động chọn ở combobox mà người dùng vừa bấm nút (+)
                sender_btn = self.sender()
                if sender_btn == self.ui.btn_add_base_unit:
                    self.ui.cbo_base_unit.setCurrentIndex(self.ui.cbo_base_unit.count() - 1)
                else:
                    self.ui.cbo_conversion_unit.setCurrentIndex(self.ui.cbo_conversion_unit.count() - 1)
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", str(e))