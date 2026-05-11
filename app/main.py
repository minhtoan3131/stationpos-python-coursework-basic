import sys
from PyQt6.QtWidgets import QApplication

# ==========================================
# IMPORT SERVICES (Tầng nghiệp vụ lõi)
# ==========================================
from app.modules.product.services.impl.supplier_service_impl import SupplierServiceImpl
from app.modules.inventory.services.impl.inventory_service_impl import InventoryServiceImpl

# ==========================================
# IMPORT CONTROLLER (Tầng giao diện UI)
# ==========================================
from app.ui.inventory.controllers.inventory_management_controller import InventoryManagementController

def main():
    app = QApplication(sys.argv)

    # 1. Khởi tạo Service rỗng
    # (Vì bên trong __init__ của Service chúng ta đã bỏ khai báo Repo,
    # Service sẽ tự động lấy DatabaseConnection mỗi khi thực thi hàm)
    supplier_service = SupplierServiceImpl()
    inventory_service = InventoryServiceImpl()

    # 2. Khởi tạo UI Controller
    window = InventoryManagementController(
        inventory_service=inventory_service,
        supplier_service=supplier_service
    )

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()