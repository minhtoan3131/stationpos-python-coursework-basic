from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from app.core.database.unit_of_work import UnitOfWork
from app.ui.main_window.ui_main_window import Ui_MainWindow

from app.modules.product.services.impl.category_service_impl import CategoryServiceImpl
from app.modules.product.services.impl.supplier_service_impl import SupplierServiceImpl
from app.modules.product.services.impl.unit_service_impl import UnitServiceImpl
from app.modules.product.services.impl.product_service_impl import ProductServiceImpl
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl

from app.ui.inventory.controllers.inventory_management_controller import InventoryManagementController
from app.ui.product.controllers.product_management_controller import ProductManagementController
from app.ui.report.controllers.report_management_controller import ReportManagementController
from app.ui.sale.controllers.sales_management_controller import SalesManagementController
from app.ui.tax.controllers.tax_management_controller import TaxManagementController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.category_service = CategoryServiceImpl()
        self.supplier_service = SupplierServiceImpl()
        self.unit_service = UnitServiceImpl()
        self.product_service = ProductServiceImpl()
        self.inventory_service = InventoryServiceImpl(uow_factory=UnitOfWork)
        self.sale_service = SaleServiceImpl(uow_factory=UnitOfWork)

        # Xử lý UI cho macOS và Hiệu ứng
        self.fix_macos_font_issue()
        self.apply_sidebar_shadow()

        self.init_pages()

        self.ui.sidebar_menu.currentRowChanged.connect(self.switch_module)

        # Mặc định mở Dashboard (Index 0)
        self.ui.sidebar_menu.setCurrentRow(0)

    def apply_sidebar_shadow(self):
        """Thay thế cho box-shadow CSS không hoạt động trong PyQt"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(4)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.ui.frame_sidebar.setGraphicsEffect(shadow)

    def fix_macos_font_issue(self):
        """Ép in đậm font chữ cho Sidebar trên macOS"""
        mac_font = QFont()
        mac_font.setPointSize(16)
        mac_font.setBold(True)
        self.ui.sidebar_menu.setFont(mac_font)

    def init_pages(self):
        """Khởi tạo các widget con và đẩy vào QStackedWidget"""

        # Page 1: Quản lý sản phẩm
        self.page_product = ProductManagementController(
            product_service=self.product_service,
            category_service=self.category_service,
            supplier_service=self.supplier_service,
            unit_service=self.unit_service
        )

        # Page 2: Quản lý kho
        self.page_inventory = InventoryManagementController(
            inventory_service=self.inventory_service,
            supplier_service=self.supplier_service
        )

        # Quản lý Bán hàng
        self.page_sales = SalesManagementController(
            inventory_service=self.inventory_service,
            product_service=self.product_service,
            sale_service=self.sale_service
        )

        self.page_reports = ReportManagementController()
        self.page_tax = TaxManagementController()
        self.page_settings = self.create_placeholder("⚙️ Cấu hình Hệ thống\n(Đang phát triển)")

        # Thêm vào stack theo đúng thứ tự index của sidebar_menu
        self.ui.content_stack.addWidget(self.page_product)  # Index 0
        self.ui.content_stack.addWidget(self.page_inventory)  # Index 1
        self.ui.content_stack.addWidget(self.page_sales)  # Index 2
        self.ui.content_stack.addWidget(self.page_reports)  # Index 3
        self.ui.content_stack.addWidget(self.page_tax)  # Index 4
        self.ui.content_stack.addWidget(self.page_settings)  # Index 5

    def create_placeholder(self, text: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #94a3b8; font-size: 24px; font-weight: bold;")
        layout.addWidget(label)
        return widget

    def switch_module(self, index: int):
        """Xử lý đổi tab và tự động refresh dữ liệu"""
        self.ui.content_stack.setCurrentIndex(index)

        # Lazy Loading: Chỉ load dữ liệu khi người dùng nhấn vào tab đó
        if index == 0:
            self.page_product.load_products()
        elif index == 1:
            self.page_inventory.handle_search()
        elif index == 2:
            self.page_sales.handle_search()

    def closeEvent(self, event):
        """Đóng ứng dụng an toàn"""
        event.accept()