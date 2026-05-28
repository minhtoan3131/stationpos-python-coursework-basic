# app/core/database/unit_of_work.py
from app.core.database.connection import DatabaseConnection
from app.modules.inventory.repositories.impl.inventory_repository_impl import InventoryRepositoryImpl
from app.modules.inventory.repositories.impl.po_history_repository_impl import PurchaseOrderHistoryRepositoryImpl
from app.modules.product.repositories.impl.product_repository_impl import ProductRepositoryImpl
from app.modules.product.repositories.impl.supplier_repository_impl import SupplierRepositoryImpl
from app.modules.report.repositories.impl.report_repository_impl import ReportRepositoryImpl
from app.modules.sale.repositories.impl.invoice_history_repository_impl import InvoiceHistoryRepositoryImpl
from app.modules.sale.repositories.impl.sale_repository_impl import SaleRepositoryImpl
from app.modules.setting.repositories.impl.setting_repository_impl import SettingRepositoryImpl
from app.modules.tax.repositories.impl.tax_repository_impl import TaxReportRepository, \
    TaxLedgerRepository


class UnitOfWork:
    """
    Quản lý một 'Phiên giao dịch' (Transaction) duy nhất.
    Đảm bảo tất cả các Repo dùng chung 1 Connection.
    Tự động Commit nếu thành công, Rollback nếu có lỗi và đóng kết nối.
    """

    def __init__(self):
        self.connection = None

    def __enter__(self):
        # Mở kết nối MỚI
        self.connection = DatabaseConnection.get_connection()
        self.connection.autocommit = False  # Tắt auto-commit để dùng Transaction

        # Khởi tạo các Repo và bơm chung 1 connection vào
        self.inventory_repo = InventoryRepositoryImpl(self.connection)
        self.product_repo = ProductRepositoryImpl(self.connection)
        self.supplier_repo = SupplierRepositoryImpl(self.connection)
        self.sale_repo = SaleRepositoryImpl(self.connection)
        self.report_repo = ReportRepositoryImpl(self.connection)
        self.tax_report_repo = TaxReportRepository(self.connection)
        self.tax_ledger_repo = TaxLedgerRepository(self.connection)
        self.setting_repo = SettingRepositoryImpl(self.connection)
        self.po_history_repo = PurchaseOrderHistoryRepositoryImpl(self.connection)
        self.invoice_history_repo = InvoiceHistoryRepositoryImpl(self.connection)

        return self

    def __exit__(self, exc_type, exc_val, traceback):
        # Kết thúc khối 'with': Xử lý Transaction và ĐÓNG kết nối
        try:
            if exc_type is not None:
                self.connection.rollback()  # Có lỗi -> Rollback
            else:
                self.connection.commit()  # Không lỗi -> Commit
        finally:
            self.connection.close()  # LUÔN LUÔN trả kết nối về Pool