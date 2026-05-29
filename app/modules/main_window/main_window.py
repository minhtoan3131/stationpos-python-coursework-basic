from datetime import datetime
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QDialog, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from app.core.database.unit_of_work import UnitOfWork
from app.modules.dashboard.ui.controllers.home_welcome_controller import HomeWelcomeController
from app.modules.inventory.services.impl.po_history_service_impl import PurchaseOrderHistoryServiceImpl
from app.modules.main_window.ui_main_window import Ui_MainWindow

from app.modules.product.services.impl.category_service_impl import CategoryServiceImpl
from app.modules.product.services.impl.supplier_service_impl import SupplierServiceImpl
from app.modules.product.services.impl.unit_service_impl import UnitServiceImpl
from app.modules.product.services.impl.product_service_impl import ProductServiceImpl
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl
from app.modules.sale.services.impl.invoice_history_service_impl import InvoiceHistoryServiceImpl
from app.modules.sale.services.impl.sale_service_impl import SaleServiceImpl
from app.modules.report.services.impl.report_service_impl import ReportServiceImpl
from app.modules.setting.services.impl.setting_service_impl import SettingServiceImpl
from app.modules.setting.services.impl.store_config_service_impl import StoreConfigServiceImpl
from app.modules.setting.ui.controllers.lock_screen_dialog import LockScreenDialog
from app.modules.setting.ui.controllers.setting_management_controller import SettingManagementController
from app.modules.tax.services.impl.tax_service_impl import TaxService


from app.modules.inventory.ui.controllers.inventory_management_controller import InventoryManagementController
from app.modules.product.ui.controllers.product_management_controller import ProductManagementController
from app.modules.report.ui.controllers.report_management_controller import ReportManagementController
from app.modules.sale.ui.controllers.sales_management_controller import SalesManagementController
from app.modules.tax.ui.controllers.tax_management_controller import TaxManagementController


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
        self.report_service = ReportServiceImpl(uow_factory=UnitOfWork)
        self.tax_service = TaxService(uow_factory=UnitOfWork)
        self.setting_service = SettingServiceImpl(uow_factory=UnitOfWork)
        self.po_history_service = PurchaseOrderHistoryServiceImpl(uow_factory=UnitOfWork)

        self.invoice_history_service = InvoiceHistoryServiceImpl(uow_factory=UnitOfWork)
        self.store_config_service = StoreConfigServiceImpl(uow_factory=UnitOfWork)

        # Xử lý UI cho macOS và Hiệu ứng
        self.fix_macos_font_issue()
        self.apply_sidebar_shadow()

        self.init_pages()

        self.ui.sidebar_menu.currentRowChanged.connect(self.switch_module)
        self.ui.btn_lock_app.clicked.connect(self.handle_lock_application)

        # Mặc định mở Trang chủ (Index 0) ngay khi khởi động ứng dụng
        self.ui.sidebar_menu.setCurrentRow(0)

        self._is_first_launch = True

    def apply_sidebar_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(4)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.ui.frame_sidebar.setGraphicsEffect(shadow)

    def fix_macos_font_issue(self):
        mac_font = QFont()
        mac_font.setPointSize(16)
        mac_font.setBold(True)
        self.ui.sidebar_menu.setFont(mac_font)

    def init_pages(self):
        # Khởi tạo trang Home điều phối hành động mới
        self.page_home = HomeWelcomeController(
            report_service=self.report_service,
            inventory_service=self.inventory_service,
            tax_service=self.tax_service
        )
        # Kết nối sự kiện liên kết sâu (Deep-linking Macro) bắn ra từ trang chủ
        self.page_home.navigation_requested.connect(self.handle_home_deep_linking)

        self.page_product = ProductManagementController(
            product_service=self.product_service,
            category_service=self.category_service,
            supplier_service=self.supplier_service,
            unit_service=self.unit_service
        )

        self.page_inventory = InventoryManagementController(
            inventory_service=self.inventory_service,
            supplier_service=self.supplier_service,
            po_history_service=self.po_history_service
        )

        self.page_sales = SalesManagementController(
            inventory_service=self.inventory_service,
            product_service=self.product_service,
            sale_service=self.sale_service,
            invoice_history_service=self.invoice_history_service,
            store_config_service=self.store_config_service
        )

        self.page_reports = ReportManagementController(
            report_service=self.report_service
        )

        self.page_tax = TaxManagementController(
            tax_service=self.tax_service,
            setting_service=self.setting_service
        )

        self.page_settings = SettingManagementController(
            store_config_service=self.store_config_service
            # security_service=self.security_service,
            # backup_service=self.backup_service
        )
        # Thêm các trang vào content_stack (Thứ tự khớp chính xác 100% với file .ui)
        self.ui.content_stack.addWidget(self.page_home)  # Index 0
        self.ui.content_stack.addWidget(self.page_product)  # Index 1
        self.ui.content_stack.addWidget(self.page_inventory)  # Index 2
        self.ui.content_stack.addWidget(self.page_sales)  # Index 3
        self.ui.content_stack.addWidget(self.page_reports)  # Index 4
        self.ui.content_stack.addWidget(self.page_tax)  # Index 5
        self.ui.content_stack.addWidget(self.page_settings)  # Index 6

    def create_placeholder(self, text: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #94a3b8; font-size: 24px; font-weight: bold;")
        layout.addWidget(label)
        return widget

    def switch_module(self, index: int):
        self.ui.content_stack.setCurrentIndex(index)

        if index == 0:
            self.page_home.refresh_dashboard()
        elif index == 1:
            self.page_product.load_products()
        elif index == 2:
            self.page_inventory.handle_search()
        elif index == 3:
            self.page_sales.handle_search()
        elif index == 4:
            self.page_reports.handle_filter_today()
        elif index == 5:
            current_year = datetime.now().year
            self.page_tax.load_data_for_year(current_year)
            if hasattr(self.page_tax, 'load_history_master_table'):
                self.page_tax.load_history_master_table()
        elif index == 6:
            # Sẽ gọi hàm kéo dữ liệu Database lên đây (hiện tại ta cứ gọi sẵn)
            if hasattr(self.page_settings, 'load_current_settings'):
                self.page_settings.load_current_settings()

    def handle_home_deep_linking(self, target_index: int, search_keyword: str):
        """Macro xử lý liên kết sâu nhận lệnh từ trang chủ để chuyển module và điền sẵn bộ lọc"""
        # Đồng bộ trạng thái dòng chọn của menu bar trái và stack widget
        self.ui.sidebar_menu.setCurrentRow(target_index)
        self.switch_module(target_index)

        # Nếu trang đích là Quản lý Kho (Index 2), tự điền SKU lỗi và chạy tìm kiếm lập tức
        if target_index == 2 and search_keyword:
            if hasattr(self.page_inventory, 'ui') and hasattr(self.page_inventory.ui, 'txt_search_inventory'):
                self.page_inventory.ui.txt_search_inventory.setText(search_keyword)
                self.page_inventory.handle_search()

    def closeEvent(self, event):
        event.accept()

    def setVisible(self, visible):
        """
        Ghi đè hàm cốt lõi của Qt.
        Khi bên ngoài gọi lệnh show(), showMaximized()... luồng xử lý sẽ đi qua đây.
        """
        # Nếu đang có lệnh yêu cầu hiển thị (visible = True) VÀ là lần bật app đầu tiên
        if visible and getattr(self, '_is_first_launch', False):
            self._is_first_launch = False

            # Gọi màn hình khóa ngay lập tức
            QTimer.singleShot(0, self.handle_startup_lock)

            # CỰC KỲ QUAN TRỌNG: Lệnh return này chém đứt luồng chạy,
            # không cho cửa sổ chính (MainWindow) kịp vẽ ra màn hình, loại bỏ 100% hiện tượng chớp nháy!
            return

            # Các lần sau (hoặc khi visible = False) thì cho phép ẩn/hiện bình thường
        super().setVisible(visible)

    def handle_startup_lock(self):
        """Xử lý màn hình khóa khi vừa mở phần mềm"""
        # Không cần lệnh self.hide() ở đây vì cửa sổ chính vốn dĩ chưa hề hiện lên
        dialog = LockScreenDialog(setting_service=self.setting_service)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.showMaximized()  # Đăng nhập đúng mới thực sự vẽ cửa sổ chính ra
        else:
            QApplication.instance().quit()

    def handle_lock_application(self):
        """Xử lý khi người dùng bấm nút 'Khóa màn hình' ở thanh Menu bên trái"""
        self.hide()  # Lúc này app đang mở, nên phải ẩn đi
        self.handle_startup_lock()  # Tái sử dụng lại logic xác thực ở trên