from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from app.ui.main_window.ui_main_window import Ui_MainWindow

# ----------------- IMPORT SERVICES (Bản mới tự quản lý connection) -----------------
from app.modules.product.services.impl.category_service_impl import CategoryServiceImpl
from app.modules.product.services.impl.supplier_service_impl import SupplierServiceImpl
from app.modules.product.services.impl.unit_service_impl import UnitServiceImpl
from app.modules.product.services.impl.product_service_impl import ProductServiceImpl
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl

# ----------------- IMPORT CONTROLLERS -----------------
from app.ui.inventory.controllers.inventory_management_controller import InventoryManagementController
from app.ui.product.controllers.product_management_controller import ProductManagementController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.category_service = CategoryServiceImpl()
        self.supplier_service = SupplierServiceImpl()
        self.unit_service = UnitServiceImpl()
        self.product_service = ProductServiceImpl()
        self.inventory_service = InventoryServiceImpl()

        # Xử lý UI cho macOS và Hiệu ứng
        self.fix_macos_font_issue()
        self.apply_sidebar_shadow()

        # 3. Khởi tạo các Page (Controllers)
        self.init_pages()

        # 4. Kết nối sự kiện menu
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

        # Các Page khác (Placeholder)
        self.page_sales = self.create_placeholder("🛒 Bán hàng tại quầy\n(Đang phát triển)")
        self.page_reports = self.create_placeholder("📊 Báo cáo và thống kê\n(Đang phát triển)")
        self.page_tax = self.create_placeholder("🧾 Quản lý Thuế\n(Đang phát triển)")
        self.page_settings = self.create_placeholder("⚙️ Cấu hình Hệ thống\n(Đang phát triển)")

        # Thêm vào stack theo đúng thứ tự index của sidebar_menu
        self.ui.content_stack.addWidget(self.page_product)    # Index 0
        self.ui.content_stack.addWidget(self.page_inventory)  # Index 1
        self.ui.content_stack.addWidget(self.page_sales)      # Index 2
        self.ui.content_stack.addWidget(self.page_reports)    # Index 3
        self.ui.content_stack.addWidget(self.page_tax)        # Index 4
        self.ui.content_stack.addWidget(self.page_settings)   # Index 5

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

    def closeEvent(self, event):
        """Đóng ứng dụng an toàn"""
        event.accept()